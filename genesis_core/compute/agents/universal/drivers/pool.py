#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from __future__ import annotations

import logging
import sys
import typing as tp
import collections
import uuid as sys_uuid


from restalchemy.dm import properties
from restalchemy.dm import types
from gcl_sdk.agents.universal.drivers import meta
from gcl_sdk.agents.universal.drivers import exceptions as driver_exc

from genesis_core.common import utils
from genesis_core.compute.dm import models
from genesis_core.compute import constants as nc
from genesis_core.compute.machine.pool.driver import base as driver_base
from genesis_core.compute.machine.pool.driver import (
    exceptions as pool_exceptions,
)

LOG = logging.getLogger(__name__)


class RootVolumeNotFound(driver_exc.AgentDriverException):
    __template__ = "Root volume not found for machine {machine}."
    machine: sys_uuid.UUID


class MetaMachinePool(meta.MetaCoordinatorDataPlaneModel):
    """Machine pool meta model."""

    __driver_map__ = {}

    driver_spec = properties.property(types.Dict(), required=True)
    machine_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )
    all_cores = properties.property(types.Integer(), default=0)
    all_ram = properties.property(types.Integer(), default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dp_machine_map = {}
        self.dp_volume_map = {}

    def get_resource_ignore_fields(self) -> set[str]:
        """Return fields that should not belong to the resource."""
        return {
            "target_fields",
            "dp_machine_map",
            "dp_volume_map",
        }

    def load_driver(self) -> driver_base.AbstractPoolDriver:
        """
        Load the driver for the machine pool.

        The driver is restored from the cache if it is already loaded.
        """
        driver_key = str(self.driver_spec)

        if driver_key in self.__driver_map__:
            return self.__driver_map__[driver_key]

        # TODO(akremenetsky): Use dynamic typing for this field
        driver_kind = self.driver_spec["driver"]

        class_ = utils.load_from_entry_point(
            nc.EP_MACHINE_POOL_DRIVERS, driver_kind
        )
        driver = class_(self)
        self.__driver_map__[driver_key] = driver
        return driver

    def get_meta_model_fields(self) -> set[str] | None:
        """Return a list of meta fields or None.

        Meta fields are the fields that cannot be fetched from
        the data plane or we just want to save them into the meta file.

        `None` means all fields are meta fields but it doesn't mean they
        won't be updated from the data plane.
        """
        return {"uuid", "driver_spec", "machine_type"}

    def restore_from_dp(self, **kwargs) -> None:
        """Load the pool information."""
        driver = self.load_driver()
        self.dp_machine_map = {m.uuid: m for m in driver.list_machines()}
        self.dp_volume_map = {v.uuid: v for v in driver.list_volumes()}

        # self.dp_volumes_per_machine = collections.defaultdict(list)
        # for volume in self.dp_volume_map.values():
        #     self.dp_volumes_per_machine[volume.machine].append(volume)

        # TODO(akremenetsky): Rework this part
        self.all_cores = 10
        self.all_ram = 256000


class MetaVolume(meta.MetaCoordinatorDataPlaneModel):
    """Volume meta model."""

    size = properties.property(types.Integer(min_value=1, max_value=1000000))
    boot = properties.property(types.Boolean(), default=True)
    label = properties.property(
        types.AllowNone(types.String(max_length=127)), default=None
    )
    device_type = properties.property(
        types.Enum([t.value for t in nc.VolumeType]),
        default=nc.VolumeType.QCOW2.value,
    )
    index = properties.property(
        types.Integer(min_value=-1, max_value=1024),
        default=-1,
    )
    path = properties.property(
        types.AllowNone(types.String(max_length=255)), default=None
    )
    machine = properties.property(types.AllowNone(types.UUID()), default=None)
    node = properties.property(types.AllowNone(types.UUID()), default=None)
    status = properties.property(
        types.Enum([s.value for s in nc.VolumeStatus]),
        default=nc.VolumeStatus.NEW.value,
    )

    def _from_dp_volume(self, dp_volume: models.MachineVolume) -> None:
        self.size = dp_volume.size
        self.index = dp_volume.index
        self.machine = dp_volume.machine
        self.node = dp_volume.node
        self.device_type = dp_volume.device_type
        self.path = dp_volume.path
        self.status = dp_volume.status

    def _actualize_attachment(
        self, pool: MetaMachinePool, dp_volume: models.MachineVolume
    ) -> None:
        """Actualize the attachment of the volume."""
        # Nothing to do if the volume's machine is correct
        if self.machine == dp_volume.machine:
            return

        driver = pool.load_driver()

        # Detach the volume
        if self.machine is None:
            self._detach_volume(pool, driver, dp_volume)
            return

        # Attach the volume
        if dp_volume.machine is None:
            dp_volume.machine = self.machine
            self._attach_volume(pool, driver, dp_volume)
            return

        # Reattach from one machine to another
        self._detach_volume(pool, driver, dp_volume)
        dp_volume.machine = self.machine
        self._attach_volume(pool, driver, dp_volume)

    def _create_volume(
        self,
        pool: MetaMachinePool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        dp_volume = driver.create_volume(dp_volume)
        self.path = dp_volume.path
        self.status = dp_volume.status
        LOG.info("The volume %s created", self.uuid)

        # Update the volume in the pool
        # pool.dp_volume_map[self.uuid] = dp_volume

    def _delete_volume(
        self,
        pool: MetaMachinePool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        driver.delete_volume(dp_volume)
        LOG.info("The volume %s deleted", self.uuid)

        # Update the volume in the pool
        # del pool.dp_volume_map[self.uuid]

    def _attach_volume(
        self,
        pool: MetaMachinePool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        driver.attach_volume(dp_volume)
        LOG.info(
            "The volume %s attached to the machine %s",
            self.uuid,
            self.machine,
        )

        # Update the volume in the pool
        # pool.dp_volumes_per_machine[self.machine].append(dp_volume)

    def _detach_volume(
        self,
        pool: MetaMachinePool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        if dp_volume.machine is None:
            LOG.debug(
                "The volume %s doesn't have a machine, skip detaching",
                self.uuid,
            )
            return

        driver.detach_volume(dp_volume)
        LOG.info(
            "The volume %s detached from the machine %s",
            self.uuid,
            dp_volume.machine,
        )

        # Update the volume in the pool
        # pool.dp_volumes_per_machine[dp_volume.machine].remove(dp_volume)

    def get_meta_model_fields(self) -> set[str] | None:
        """Return a list of meta fields or None.

        Meta fields are the fields that cannot be fetched from
        the data plane or we just want to save them into the meta file.

        `None` means all fields are meta fields but it doesn't mean they
        won't be updated from the data plane.
        """
        return {
            "uuid",
            "boot",
            "label",
            "node",
        }

    def dump_to_dp(self, pool: MetaMachinePool) -> None:
        """Create the volume to the data plane."""
        if self.uuid in pool.dp_volume_map:
            dp_volume = pool.dp_volume_map[self.uuid]
            self._from_dp_volume(dp_volume)
            raise driver_exc.ResourceAlreadyExists(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_volume = models.MachineVolume(
            uuid=self.uuid,
            size=self.size,
            boot=self.boot,
            label=self.label,
            device_type=self.device_type,
            index=self.index,
            # TODO(akremenetsky): Detect machine without volume name
            machine=self.machine,
            node=self.node,
            path=self.path,
        )
        self._create_volume(pool, driver, dp_volume)

        # The volume without machine, just create and exit.
        if self.machine is None:
            return

        # Don't attach volumes if they belongs to a machine
        # but the machine doesn't exist.
        if self.machine not in pool.dp_machine_map:
            LOG.debug(
                "The machine %s doesn't exist, skip attaching", self.machine
            )
            return

        # It's a root volume. It will be attached in the machine model.
        if self.index == 0:
            return

        self._attach_volume(pool, driver, dp_volume)

    def restore_from_dp(self, pool: MetaMachinePool) -> None:
        """Load the pool information."""
        if self.uuid not in pool.dp_volume_map:
            raise driver_exc.ResourceNotFound(resource=self)

        dp_volume = pool.dp_volume_map[self.uuid]
        self._from_dp_volume(dp_volume)

    def delete_from_dp(self, pool: MetaMachinePool) -> None:
        """Delete the resource from the data plane."""
        if self.uuid not in pool.dp_volume_map:
            raise driver_exc.ResourceNotFound(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_volume = pool.dp_volume_map[self.uuid]
        self._detach_volume(pool, driver, dp_volume)
        self._delete_volume(pool, driver, dp_volume)

    def update_on_dp(self, pool: MetaMachinePool) -> None:
        """Update the resource on the data plane."""
        if self.uuid not in pool.dp_volume_map:
            raise driver_exc.ResourceNotFound(resource=self)

        dp_volume: models.MachineVolume = pool.dp_volume_map[self.uuid]
        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        unknown_action = True

        # Resize the volume
        if self.size != dp_volume.size:
            unknown_action = False
            dp_volume.size = self.size
            driver.resize_volume(dp_volume)
            LOG.info("The volume %s resized.", self.uuid)

        # Attachments
        if self.machine != dp_volume.machine:
            unknown_action = False
            self._actualize_attachment(pool, dp_volume)

        if unknown_action:
            LOG.error("Unknown volume action")


class MetaMachine(meta.MetaCoordinatorDataPlaneModel):
    """Machine meta model."""

    cores = properties.property(
        types.Integer(min_value=0, max_value=4096), required=True
    )
    ram = properties.property(types.Integer(min_value=0), required=True)
    status = properties.property(
        types.Enum([s.value for s in nc.MachineStatus]),
        default=nc.MachineStatus.NEW.value,
    )
    machine_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )
    node = properties.property(types.AllowNone(types.UUID()), default=None)
    pool = properties.property(types.AllowNone(types.UUID()))
    boot = properties.property(
        types.Enum([b.value for b in nc.BootAlternative]),
        default=nc.BootAlternative.network.value,
    )

    # UUID from the firmware of the machine
    firmware_uuid = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
    )

    # Actual image of the machine
    image = properties.property(
        types.AllowNone(types.String(max_length=255)), default=None
    )

    def _create_machine(
        self,
        driver: driver_base.AbstractPoolDriver,
        dp_machine: models.Machine,
    ) -> None:
        dp_machine = driver.create_machine(dp_machine)
        self.status = dp_machine.status
        LOG.info("The machine %s created", self.uuid)

        # Update the machine in the pool
        # pool.dp_machine_map[self.uuid] = dp_machine

    def _delete_machine(
        self,
        driver: driver_base.AbstractPoolDriver,
    ) -> None:
        driver.delete_machine(dp_machine)
        LOG.info("The machine %s deleted", self.uuid)

        # Update the machine in the pool
        # del pool.dp_machine_map[self.uuid]

    def _from_dp_machine(self, dp_machine: models.Machine) -> None:
        self.cores = dp_machine.cores
        self.ram = dp_machine.ram
        self.status = dp_machine.status

    def get_meta_model_fields(self) -> set[str] | None:
        """Return a list of meta fields or None.

        Meta fields are the fields that cannot be fetched from
        the data plane or we just want to save them into the meta file.

        `None` means all fields are meta fields but it doesn't mean they
        won't be updated from the data plane.
        """
        return {
            "uuid",
            "machine_type",
            "node",
            "pool",
            "boot",
            "firmware_uuid",
            "image",
        }

    def dump_to_dp(
        self, pool: MetaMachinePool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Create the machine in the pool."""
        if self.uuid in pool.dp_machine_map:
            dp_machine = pool.dp_machine_map[self.uuid]
            self._from_dp_machine(dp_machine)
            raise driver_exc.ResourceAlreadyExists(resource=self)

        # Validation all resources are ready for the machine
        volumes = sorted(volumes, key=lambda v: v.index)

        # Root volume must be the first
        if not volumes or volumes[0].index != 0:
            raise RootVolumeNotFound(machine=self.uuid)

        # TODO(akremenetsky): Validate ports

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_machine = models.Machine(
            uuid=self.uuid,
            cores=self.cores,
            ram=self.ram,
            machine_type=self.machine_type,
            node=self.node,
            pool=self.pool,
            boot=self.boot,
            firmware_uuid=self.firmware_uuid,
            image=self.image,
        )
        self._create_machine(driver, dp_machine)

    def restore_from_dp(
        self, pool: MetaMachinePool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Load the machine from the data plane."""
        if self.uuid not in pool.dp_machine_map:
            raise driver_exc.ResourceNotFound(resource=self)

        dp_machine = pool.dp_machine_map[self.uuid]
        self._from_dp_machine(dp_machine)

    def delete_from_dp(
        self, pool: MetaMachinePool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Delete the machine from the data plane."""
        if self.uuid not in pool.dp_machine_map:
            raise driver_exc.ResourceNotFound(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_machine = pool.dp_machine_map[self.uuid]
        self._delete_machine(driver, dp_machine)

    def update_on_dp(
        self, pool: MetaMachinePool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Update the machine on the data plane."""
        if self.uuid not in pool.dp_machine_map:
            raise driver_exc.ResourceNotFound(resource=self)

        dp_machine: models.Machine = pool.dp_machine_map[self.uuid]
        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        unknown_action = True

        # Cores
        if self.cores != dp_machine.cores:
            unknown_action = False
            driver.set_machine_cores(dp_machine, self.cores)
            LOG.info("The machine %s cores updated.", self.uuid)

        # Ram
        if self.ram != dp_machine.ram:
            unknown_action = False
            driver.set_machine_ram(dp_machine, self.ram)
            LOG.info("The machine %s ram updated.", self.uuid)

        # Boot
        # if self.boot != dp_machine.boot:
        #     unknown_action = False
        #     driver.set_machine_boot(dp_machine, self.boot)
        #     LOG.info("The machine %s boot updated.", self.uuid)

        # # Image
        # if self.image != dp_machine.image:
        #     unknown_action = False
        #     driver.set_machine_image(dp_machine, self.image)
        #     LOG.info("The machine %s image updated.", self.uuid)

        if unknown_action:
            LOG.error("Unknown machine update action")


class PoolAgentDriver(meta.MetaCoordinatorAgentDriver):

    # Order matters
    __model_map__ = {
        "machine_pool": MetaMachinePool,
        "machine_volume": MetaVolume,
        "machine": MetaMachine,
    }

    __coordinator_map__ = {
        "machine_pool": {},
        "machine": {
            "pool": {
                "kind": "machine_pool",
                "relation": "machine:pool",
            },
            "volumes": {
                "kind": "volume",
                "relation": "volume:machine",
            },
        },
    }
