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
import typing as tp
import uuid as sys_uuid

import netaddr

from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from gcl_sdk.agents.universal.drivers import meta
from gcl_sdk.agents.universal.drivers import exceptions as ua_driver_exc

from genesis_core.common import utils
from genesis_core.compute.dm import models
from genesis_core.compute import constants as nc
from genesis_core.compute.pool.drivers import base as driver_base
from genesis_core.compute.pool.drivers import exceptions as driver_exc


LOG = logging.getLogger(__name__)


class RootVolumeNotFound(ua_driver_exc.AgentDriverException):
    __template__ = "Root volume not found for machine {machine}."
    machine: sys_uuid.UUID


class MetaPool(meta.MetaCoordinatorDataPlaneModel):
    """Machine pool meta model."""

    __driver_map__ = {}

    driver_spec = properties.property(types.Dict(), required=True)
    machine_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )
    all_cores = properties.property(types.Integer(), default=0)
    all_ram = properties.property(types.Integer(), default=0)
    avail_cores = properties.property(types.Integer(), default=0)
    avail_ram = properties.property(types.Integer(), default=0)
    cores_ratio = properties.property(types.Float(min_value=0.0), default=1.0)
    ram_ratio = properties.property(types.Float(min_value=0.0), default=1.0)
    status = properties.property(
        types.Enum([s.value for s in nc.MachinePoolStatus]),
        default=nc.MachinePoolStatus.ACTIVE.value,
    )
    storage_pools = properties.property(
        types.TypedList(
            types_dynamic.KindModelSelectorType(
                types_dynamic.KindModelType(models.ThinStoragePool),
            ),
        ),
        default=list,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dp_machine_map = {}
        self.dp_volume_map = {}
        self.dp_storage_pool_map = {}

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
        pool_info, storage_pools, machines, volumes = (
            driver.list_pool_resources()
        )
        self.dp_machine_map = {m.uuid: m for m in machines}
        self.dp_volume_map = {v.uuid: v for v in volumes}
        self.dp_storage_pool_map = {p.uuid: p for p in storage_pools}

        # NOTE(akremenetsky): Use only the storage pool specified in the
        # driver spec.
        self.storage_pools = list(storage_pools)

        self.all_cores = int(pool_info.all_cores * self.cores_ratio)
        self.all_ram = int(pool_info.all_ram * self.ram_ratio)
        self.avail_cores = self.all_cores - sum(
            m.cores for m in self.dp_machine_map.values()
        )
        self.avail_ram = self.all_ram - sum(
            m.ram for m in self.dp_machine_map.values()
        )

    def dump_to_dp(self, **kwargs) -> None:
        """Configure the pool."""
        # Actually we do nothing to configure or dump to pool at the moment
        # but we need to synchronize the pool state since it will be used by
        # machines and volumes as their dependencies.
        self.restore_from_dp(**kwargs)


class MetaVolume(meta.MetaCoordinatorDataPlaneModel):
    """Volume meta model."""

    pool = properties.property(types.UUID(), required=True)
    name = properties.property(types.String(max_length=255), default=None)
    image = properties.property(
        types.AllowNone(types.String(max_length=255)), default=None
    )

    size = properties.property(types.Integer(min_value=1, max_value=1000000))
    boot = properties.property(types.Boolean(), default=True)
    label = properties.property(
        types.AllowNone(types.String(max_length=127)), default=None
    )
    device_type = properties.property(types.String(max_length=64), default="")
    index = properties.property(
        types.Integer(min_value=0, max_value=4096),
        default=4096,
    )
    machine = properties.property(types.AllowNone(types.UUID()), default=None)
    status = properties.property(
        types.Enum([s.value for s in nc.VolumeStatus]),
        default=nc.VolumeStatus.NEW.value,
    )
    project_id = properties.property(
        types.UUID(), required=True, read_only=True
    )

    def _from_dp_volume(self, dp_volume: models.MachineVolume) -> None:
        self.name = dp_volume.name
        self.size = dp_volume.size
        self.index = dp_volume.index
        self.machine = dp_volume.machine
        self.device_type = dp_volume.device_type
        self.status = dp_volume.status

    def _actualize_attachment(
        self, pool: MetaPool, dp_volume: models.MachineVolume
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
        pool: MetaPool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        dp_volume = driver.create_volume(dp_volume)
        self.status = dp_volume.status
        LOG.info("The volume %s created", self.uuid)

    def _delete_volume(
        self,
        pool: MetaPool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        driver.delete_volume(dp_volume)
        LOG.info("The volume %s deleted", self.uuid)

    def _attach_volume(
        self,
        pool: MetaPool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        try:
            driver.attach_volume(dp_volume)
        except driver_exc.VolumeAlreadyAttachedError:
            # Volume is already attached, do nothing
            LOG.warning(
                "The volume %s is already attached, do nothing",
                self.uuid,
            )
        else:
            LOG.info(
                "The volume %s attached to the machine %s",
                self.uuid,
                self.machine,
            )

    def _detach_volume(
        self,
        pool: MetaPool,
        driver: driver_base.AbstractPoolDriver,
        dp_volume: models.MachineVolume,
    ) -> None:
        if dp_volume.machine is None:
            LOG.debug(
                "The volume %s doesn't have a machine, skip detaching",
                self.uuid,
            )
            return

        try:
            driver.detach_volume(dp_volume)
        except driver_exc.VolumeNotAttachedError:
            # Volume is already detached, do nothing
            LOG.warning(
                "The volume %s is already detached, do nothing",
                self.uuid,
            )
        else:
            LOG.info(
                "The volume %s detached from the machine %s",
                self.uuid,
                dp_volume.machine,
            )

    def _to_dp_volume(self) -> models.MachineVolume:
        """Convert the volume to the data plane."""
        return models.MachineVolume(
            uuid=self.uuid,
            name=self.name,
            image=self.image,
            size=self.size,
            boot=self.boot,
            label=self.label,
            device_type=self.device_type,
            index=self.index,
            machine=self.machine,
            project_id=self.project_id,
        )

    def _is_root_volume(self) -> bool:
        return self.machine and self.index == 0

    def _has_storage_capacity(
        self, pool: MetaPool, size: int | None = None
    ) -> bool:
        if not pool.storage_pools:
            return False

        size = size if size is not None else self.size

        # FIXME(akremenetsky): It's fine for current implementation
        # but we need to support multiple storage pools
        return pool.storage_pools[0].has_capacity(size)

    def _allocate_capacity(
        self, pool: MetaPool, size: int | None = None
    ) -> None:
        size = size if size is not None else self.size
        storage_pool = pool.storage_pools[0]
        storage_pool.allocate_capacity(size)

    def get_meta_model_fields(self) -> set[str] | None:
        """Return a list of meta fields or None.

        Meta fields are the fields that cannot be fetched from
        the data plane or we just want to save them into the meta file.

        `None` means all fields are meta fields but it doesn't mean they
        won't be updated from the data plane.
        """
        return {
            "uuid",
            "pool",
            "image",
            "boot",
            "label",
            "device_type",
            "project_id",
        }

    def dump_to_dp(self, pool: MetaPool) -> None:
        """Create the volume to the data plane."""
        driver: driver_base.AbstractPoolDriver = pool.load_driver()

        if self.uuid in pool.dp_volume_map:
            # The volume already exists in the data plane
            # Reuse it
            dp_volume = pool.dp_volume_map[self.uuid]
        else:
            # Check the storage pool has enough capacity
            if not self._has_storage_capacity(pool):
                self.status = nc.VolumeStatus.ERROR.value
                return

            dp_volume = models.MachineVolume(
                uuid=self.uuid,
                name=self.name,
                image=self.image,
                size=self.size,
                boot=self.boot,
                label=self.label,
                device_type=self.device_type,
                index=self.index,
                # TODO(akremenetsky): Detect machine without volume name
                machine=self.machine,
                project_id=self.project_id,
            )
            self._create_volume(pool, driver, dp_volume)
            self._allocate_capacity(pool)

        self._from_dp_volume(dp_volume)

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
        if self._is_root_volume():
            return

        self._attach_volume(pool, driver, dp_volume)

    def restore_from_dp(self, pool: MetaPool | None) -> None:
        """Load the pool information."""
        # Prevent actualization when pool is not provided
        if pool is None:
            raise ValueError(
                f"The pool is not provided for volume {self.uuid}"
            )

        if self.uuid not in pool.dp_volume_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        dp_volume = pool.dp_volume_map[self.uuid]
        self._from_dp_volume(dp_volume)

    def delete_from_dp(self, pool: MetaPool) -> None:
        """Delete the resource from the data plane."""
        if self.uuid not in pool.dp_volume_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_volume = pool.dp_volume_map[self.uuid]
        self._detach_volume(pool, driver, dp_volume)
        self._delete_volume(pool, driver, dp_volume)

    def update_on_dp(self, pool: MetaPool) -> None:
        """Update the resource on the data plane."""
        if self.uuid not in pool.dp_volume_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_volume: models.MachineVolume = pool.dp_volume_map[self.uuid]
        machine = dp_volume.machine
        unknown_action = True

        # A special case for root volumes. If the condition is true, it
        # means the machine failed to be created on previous iteration.
        # So do nothing, just give another chance to the agent create
        # the machine.
        if self._is_root_volume() and self.machine not in pool.dp_machine_map:
            return

        # Resize the volume
        if self.size != dp_volume.size:
            # Check the storage pool has enough capacity
            if not self._has_storage_capacity(
                pool, self.size - dp_volume.size
            ):
                self.status = nc.VolumeStatus.ERROR.value
                return

            unknown_action = False
            dp_volume.size = self.size
            driver.resize_volume(dp_volume)
            self._allocate_capacity(pool, self.size - dp_volume.size)
            LOG.info("The volume %s resized.", self.uuid)

        # Attachments
        if self.machine != dp_volume.machine:
            unknown_action = False
            self._actualize_attachment(pool, dp_volume)

        # TODO(akremenetsky): Add image actualization for volumes

        if unknown_action:
            LOG.error("Unknown volume action")

        dp_volume = driver.get_volume(self.uuid)
        self._from_dp_volume(dp_volume)

        # Not all drivers support machine field on `get` operation
        self.machine = machine


class MetaMachine(meta.MetaCoordinatorDataPlaneModel):
    """Machine meta model."""

    name = properties.property(types.String(max_length=255), default="")
    cores = properties.property(
        types.Integer(min_value=0, max_value=4096), default=0
    )
    ram = properties.property(types.Integer(min_value=0), default=0)
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
    image = properties.property(
        types.AllowNone(types.String(max_length=512)), default=None
    )
    project_id = properties.property(
        types.UUID(), required=True, read_only=True
    )
    port_info = properties.property(types.Dict(), default=dict)

    def _create_machine(
        self,
        driver: driver_base.AbstractPoolDriver,
        dp_machine: models.Machine,
        volumes: tp.Collection[models.MachineVolume],
        ports: tp.Collection[models.Port],
    ) -> None:
        dp_machine = driver.create_machine(dp_machine, volumes, ports)
        self.status = dp_machine.status
        LOG.info("The machine %s created", self.uuid)

    def _delete_machine(
        self,
        driver: driver_base.AbstractPoolDriver,
        dp_machine: models.Machine,
    ) -> None:
        driver.delete_machine(dp_machine)
        LOG.info("The machine %s deleted", self.uuid)

    def _from_dp_machine(self, dp_machine: models.Machine) -> None:
        self.cores = dp_machine.cores
        self.ram = dp_machine.ram
        self.status = dp_machine.status

        # Don't try to restore image from legacy machine since it is not
        # available in the data plane. So to avoid recreation of such
        # machines just take the image from meta. For legacy machines
        # we need to fit data plane to have ability for machine update.
        self.image = dp_machine.image or self.image

    def _has_enough_resources(
        self, pool: MetaPool, cores: int | None = None, ram: int | None = None
    ) -> bool:
        if cores is not None and pool.avail_cores < cores:
            return False

        if ram is not None and pool.avail_ram < ram:
            return False

        return True

    def _allocate_resources(
        self, pool: MetaPool, cores: int | None = None, ram: int | None = None
    ) -> None:
        if cores is not None:
            pool.avail_cores -= cores

        if ram is not None:
            pool.avail_ram -= ram

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
            "project_id",
            "port_info",
            "image",
            "name",
            # Temporary get boot field from meta
            "boot",
        }

    def dump_to_dp(
        self, pool: MetaPool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Create the machine in the pool."""
        driver: driver_base.AbstractPoolDriver = pool.load_driver()

        # The machine is already present in the data plane.
        # It's not ordinary behavior but there is a couple of cases
        # where this can happen during recovery or migration.
        # So do nothing and let the `update_on_dp` handle it next iteration.
        # The iteration is skipped intentionally to have a chance to stop
        # the service during migration if something goes wrong.
        if self.uuid in pool.dp_machine_map:
            LOG.warning(
                "Machine %s already exists in pool %s. "
                "It will be actualized on the next iteration.",
                self.uuid,
                pool.uuid,
            )
            return

        # Validation all resources are ready for the machine
        volumes = sorted(volumes, key=lambda v: v.index)

        # Root volume must be the first
        if not volumes or volumes[0].index != 0:
            raise RootVolumeNotFound(machine=self.uuid)

        # Seems something went wrong with the root volume
        # Mark the machine is in error state as well.
        if volumes[0].status == nc.VolumeStatus.ERROR:
            self.status = nc.MachineStatus.ERROR.value
            return

        # Check the pool has enough resources.
        # If the pool doesn't have enough resources, mark the machine
        # as `NEED_RESCHEDULE` and return.
        if not self._has_enough_resources(pool, self.cores, self.ram):
            self.status = nc.MachineStatus.NEED_RESCHEDULE.value
            return

        dp_machine = models.Machine(
            uuid=self.uuid,
            name=self.name,
            cores=self.cores,
            ram=self.ram,
            machine_type=self.machine_type,
            node=self.node,
            boot=self.boot,
            image=self.image,
            project_id=self.project_id,
        )

        # Find the related entities
        pool_volumes = tuple(v._to_dp_volume() for v in volumes)

        # TODO(akremenetsky): This simplest implementation is fine while
        # we have only single flat network.
        ports = (
            models.Port(
                uuid=sys_uuid.UUID(self.port_info["uuid"]),
                subnet=sys_uuid.UUID(self.port_info["subnet"]),
                ipv4=netaddr.IPAddress(self.port_info["ipv4"]),
                mask=netaddr.IPAddress(self.port_info["mask"]),
                mac=self.port_info["mac"],
                status=nc.PortStatus.ACTIVE,
                project_id=self.project_id,
            ),
        )

        self._create_machine(driver, dp_machine, pool_volumes, ports)
        self._allocate_resources(pool, self.cores, self.ram)

    def restore_from_dp(
        self, pool: MetaPool | None, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Load the machine from the data plane."""
        # Prevent actualization when pool is not provided
        if pool is None:
            raise ValueError(
                f"The pool is not provided for machine {self.uuid}"
            )

        if self.uuid not in pool.dp_machine_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        dp_machine = pool.dp_machine_map[self.uuid]
        self._from_dp_machine(dp_machine)

    def delete_from_dp(
        self, pool: MetaPool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Delete the machine from the data plane."""
        if self.uuid not in pool.dp_machine_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        dp_machine = pool.dp_machine_map[self.uuid]
        self._delete_machine(driver, dp_machine)

    def update_on_dp(
        self, pool: MetaPool, volumes: tp.Collection[MetaVolume]
    ) -> None:
        """Update the machine on the data plane."""
        if self.uuid not in pool.dp_machine_map:
            raise ua_driver_exc.ResourceNotFound(resource=self)

        dp_machine: models.Machine = pool.dp_machine_map[self.uuid]
        driver: driver_base.AbstractPoolDriver = pool.load_driver()
        unknown_action = True

        # Cores
        if self.cores != dp_machine.cores:
            unknown_action = False

            # Mark the machine as error if the pool doesn't have enough
            # resources to update the machine. In the `create` case
            # the machine is marked as `NEED_RESCHEDULE` but it's not
            # possible in this case as we need to migrate the machine.
            # Such functionality is not implemented yet.
            need_cores = self.cores - dp_machine.cores
            if not self._has_enough_resources(pool, cores=need_cores):
                self.status = nc.MachineStatus.ERROR.value
                LOG.error(
                    "Not enough Cores to update the machine %s", self.uuid
                )
                return

            # NOTE(akremenetsky): Legacy machines always have image=None.
            # Therefore we cannot update the image without modifying XML.
            # To make things simpler, the image is enriched when cores
            # are changed. This avoids the need to modify XML directly.
            # This "helper" has to be removed after full migration.
            if dp_machine.image is None:
                dp_machine.image = self.image
                LOG.info(
                    "Enriched legacy machine %s with image %s.",
                    self.uuid,
                    self.image,
                )

            driver.set_machine_cores(dp_machine, self.cores)
            self._allocate_resources(pool, cores=need_cores)
            LOG.info("The machine %s cores updated.", self.uuid)

        # Ram
        if self.ram != dp_machine.ram:
            unknown_action = False

            # Mark the machine as error if the pool doesn't have enough
            # resources to update the machine. In the `create` case
            # the machine is marked as `NEED_RESCHEDULE` but it's not
            # possible in this case as we need to migrate the machine.
            # Such functionality is not implemented yet.
            need_ram = self.ram - dp_machine.ram
            if not self._has_enough_resources(pool, ram=need_ram):
                self.status = nc.MachineStatus.ERROR.value
                LOG.error("Not enough RAM to update the machine %s", self.uuid)
                return

            driver.set_machine_ram(dp_machine, self.ram)
            self._allocate_resources(pool, ram=need_ram)
            LOG.info("The machine %s ram updated.", self.uuid)

        # TODO(akremenetsky): Actually update image logic is more suitable for
        # volumes update but for backward compatibility we keep it here.
        # Image
        if dp_machine.image and self.image != dp_machine.image:
            unknown_action = False
            # Just recreate, Seed OS flash the new image
            dp_machine.image = self.image
            driver.recreate_machine(dp_machine)
            LOG.info("The machine %s image updated.", self.uuid)

        if unknown_action:
            LOG.error("Unknown machine update action")

        # Get the updated machine state from the driver
        updated_machine = driver.get_machine(self.uuid)
        self._from_dp_machine(updated_machine)


class PoolAgentDriver(meta.MetaCoordinatorAgentDriver):

    # Order matters
    __model_map__ = {
        "pool": MetaPool,
        "pool_volume": MetaVolume,
        "pool_machine": MetaMachine,
    }

    __coordinator_map__ = {
        "pool": {},
        "pool_volume": {
            "pool": {
                "kind": "pool",
                "relation": "pool_volume:pool",
            },
        },
        "pool_machine": {
            "pool": {
                "kind": "pool",
                "relation": "pool_machine:pool",
            },
            "volumes": {
                "kind": "pool_volume",
                "relation": "pool_volume:machine",
            },
        },
    }
