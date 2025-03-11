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

import typing as tp

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import filters as dm_filters
from restalchemy.storage.sql import orm

from genesis_core.node import constants as nc
from genesis_core.common import utils


class ModelWithFullAsset(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    models.ModelWithProject,
    models.ModelWithNameDesc,
):
    pass


class MachineAgent(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    orm.SQLStorableMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "machine_agents"

    status = properties.property(
        types.Enum([s.value for s in nc.MachineAgentStatus]),
        default=nc.MachineAgentStatus.DISABLED.value,
    )

    @classmethod
    def all_active(
        cls, limit: int | None = nc.DEF_SQL_LIMIT
    ) -> tp.List["MachineAgent"]:
        """Get all active machine agents."""
        return cls.objects.get_all(
            filters={
                "status": dm_filters.EQ(nc.MachineAgentStatus.ACTIVE.value),
            },
            limit=limit,
        )


class MachinePool(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    orm.SQLStorableWithJSONFieldsMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "machine_pools"
    __jsonfields__ = ["driver_spec"]
    __driver_map__ = {}

    driver_spec = properties.property(types.Dict(), default=lambda: {})
    agent = properties.property(types.AllowNone(types.UUID()), default=None)
    machine_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )
    status = properties.property(
        types.Enum([s.value for s in nc.MachinePoolStatus]),
        default=nc.MachinePoolStatus.DISABLED.value,
    )

    avail_cores = properties.property(types.Integer(), default=0)
    avail_ram = properties.property(types.Integer(), default=0)
    all_cores = properties.property(types.Integer(), default=0)
    all_ram = properties.property(types.Integer(), default=0)

    @property
    def has_driver(self) -> bool:
        return self.driver_spec is not None

    def load_driver(self) -> tp.Type["AbstractPoolDriver"]:
        """
        Load the driver for the machine pool.

        This method will try to load all drivers from the
        ``genesis_core.machine_pool_drivers`` entry point group and try to
        instantiate them with the current machine pool. If a driver is
        successfully loaded, it is stored in a cache for faster access.

        If no driver is found, a ValueError is raised.

        :return: The loaded driver class
        :raises ValueError: If no driver is found
        """
        driver_key = str(self.driver_spec)

        if driver_key in self.__driver_map__:
            return self.__driver_map__[driver_key]

        ep_group = utils.load_group_from_entry_point(
            nc.EP_MACHINE_POOL_DRIVERS
        )
        for e in ep_group:
            try:
                class_ = e.load()
                driver = class_(self)
                self.__driver_map__[driver_key] = driver
                return driver
            except Exception:
                # Just try another driver
                pass

        raise ValueError(f"Driver for spec '{self.driver_spec}' not found")


class Node(ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin):
    __tablename__ = "nodes"

    cores = properties.property(
        types.Integer(min_value=1, max_value=4096), required=True
    )
    ram = properties.property(types.Integer(min_value=1), required=True)
    root_disk_size = properties.property(
        types.AllowNone(types.Integer(min_value=1, max_value=1000000)),
        default=nc.DEF_ROOT_DISK_SIZE,
    )
    image = properties.property(types.String(max_length=255), required=True)
    status = properties.property(
        types.Enum([s.value for s in nc.NodeStatus]),
        default=nc.NodeStatus.NEW.value,
    )
    node_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )


class Machine(
    ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin
):
    __tablename__ = "machines"

    cores = properties.property(
        types.Integer(min_value=0, max_value=4096), required=True
    )
    ram = properties.property(types.Integer(min_value=0), required=True)
    status = properties.property(
        types.Enum([s.value for s in nc.MachineStatus]),
        default=nc.MachineStatus.ACTIVE.value,
    )
    machine_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )
    node = properties.property(types.AllowNone(types.UUID()), default=None)
    pool = properties.property(types.AllowNone(types.UUID()), default=None)
    boot = properties.property(
        types.Enum([b.value for b in nc.BootAlternative]),
        default=nc.BootAlternative.network.value,
    )

    # UUID from the firmware of the machine
    firmware_uuid = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
    )

    builder = properties.property(types.AllowNone(types.UUID()), default=None)
    build_status = properties.property(
        types.Enum([s.value for s in nc.MachineBuildStatus]),
        default=nc.MachineBuildStatus.IN_BUILD.value,
    )


class Volume(ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin):
    __tablename__ = "node_volumes"

    node = properties.property(types.AllowNone(types.UUID()))
    size = properties.property(types.Integer(min_value=1, max_value=1000000))
    boot = properties.property(types.Boolean(), default=True)
    label = properties.property(
        types.AllowNone(types.String(max_length=127)), default=None
    )
    device_type = properties.property(
        types.Enum([t.value for t in nc.VolumeType]),
        default=nc.VolumeType.QCOW2.value,
    )


class MachineVolume(Volume):
    __tablename__ = "machine_volumes"
    __custom_properties__ = {
        "path": types.AllowNone(types.String(max_length=255)),
    }

    def __init__(self, path: str | None = None, *args, **kwargs):
        self.path = path
        super().__init__(*args, **kwargs)

    machine = properties.property(types.AllowNone(types.UUID()))


class UnscheduledNode(Node):
    __tablename__ = "unscheduled_nodes"


class Netboot(
    models.ModelWithUUID, orm.SQLStorableMixin, models.SimpleViewMixin
):
    __tablename__ = "netboots"

    boot = properties.property(
        types.Enum([b.value for b in nc.BootAlternative]),
        default=nc.BootAlternative.network.value,
    )


class Builder(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "n_builders"

    status = properties.property(
        types.Enum([s.value for s in nc.BuilderStatus]),
        default=nc.BuilderStatus.ACTIVE.value,
    )


class MachinePoolReservations(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "n_machine_pool_reservations"

    pool = properties.property(types.UUID())
    machine = properties.property(types.AllowNone(types.UUID()), default=None)
    cores = properties.property(
        types.Integer(min_value=0, max_value=4096),
        required=True,
        default=0,
    )
    ram = properties.property(
        types.Integer(min_value=0), required=True, default=0
    )
