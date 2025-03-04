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

import inspect
import typing as tp

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import filters as dm_filters
from restalchemy.storage.sql import orm

from genesis_core.node import constants as nc
from genesis_core.common import utils


class DumpToSimpleViewMixin:
    def dump_to_simple_view(
        self,
        skip: tp.Optional[tp.List[str]] = None,
        save_uuid: bool = False,
        custom_properties: bool = False,
    ):
        skip = skip or []
        result = {}
        for name, prop in self.properties.properties.items():
            if name in skip:
                continue
            prop_type = prop.get_property_type()
            if save_uuid and (
                isinstance(prop_type, types.UUID)
                or (
                    isinstance(prop_type, types.AllowNone)
                    and isinstance(prop_type.nested_type, types.UUID)
                )
            ):
                result[name] = getattr(self, name)
                continue

            result[name] = prop_type.to_simple_type(getattr(self, name))

        # Convert the custom properties.
        if not custom_properties and not hasattr(
            self, "__custom_properties__"
        ):
            return result

        for name, prop_type in self.get_custom_properties():
            result[name] = prop_type.to_simple_type(getattr(self, name))

        # Nested objects may be not converted properly,
        # so try to restore at least
        if save_uuid:
            return self._restore_uuids(result)
        return result


class RestoreFromSimpleViewMixin:
    @classmethod
    def restore_from_simple_view(
        cls, skip_unknown_fields: bool = False, **kwargs
    ):
        model_format = {}
        for name, value in kwargs.items():
            name = name.replace("-", "_")

            # Ignore unknown fields
            if skip_unknown_fields and name not in cls.properties.properties:
                continue

            try:
                prop_type = cls.properties.properties[name].get_property_type()
            except KeyError:
                prop_type = cls.get_custom_property_type(name)
            prop_type = (
                type(prop_type)
                if not inspect.isclass(prop_type)
                else prop_type
            )
            if not isinstance(value, prop_type):
                try:
                    model_format[name] = (
                        cls.properties.properties[name]
                        .get_property_type()
                        .from_simple_type(value)
                    )
                except KeyError:
                    model_format[name] = cls.get_custom_property_type(
                        name
                    ).from_simple_type(value)
            else:
                model_format[name] = value
        return cls(**model_format)


class SimpleViewMixin(DumpToSimpleViewMixin, RestoreFromSimpleViewMixin):
    pass


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
    SimpleViewMixin,
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
    SimpleViewMixin,
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


class Node(ModelWithFullAsset, orm.SQLStorableMixin, SimpleViewMixin):
    __tablename__ = "nodes"

    cores = properties.property(
        types.Integer(min_value=1, max_value=4096), required=True
    )
    ram = properties.property(types.Integer(min_value=1), required=True)
    image = properties.property(types.String(max_length=255), required=True)
    status = properties.property(
        types.Enum([s.value for s in nc.NodeStatus]),
        default=nc.NodeStatus.NEW.value,
    )
    node_type = properties.property(
        types.Enum([t.value for t in nc.NodeType]),
        default=nc.NodeType.VM.value,
    )


class Machine(ModelWithFullAsset, orm.SQLStorableMixin, SimpleViewMixin):
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
    pool = properties.property(types.UUID())
    boot = properties.property(
        types.Enum([b.value for b in nc.BootAlternative]),
        default=nc.BootAlternative.network.value,
    )

    # UUID from the firmware of the machine
    firmware_uuid = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
    )


class Volume(ModelWithFullAsset, orm.SQLStorableMixin, SimpleViewMixin):
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

    machine = properties.property(types.AllowNone(types.UUID()))
    path = properties.property(
        types.AllowNone(types.String(max_length=255)), default=None
    )


class UnscheduledNode(Node):
    __tablename__ = "unscheduled_nodes"


class Netboot(models.ModelWithUUID, orm.SQLStorableMixin, SimpleViewMixin):
    __tablename__ = "netboots"

    boot = properties.property(
        types.Enum([b.value for b in nc.BootAlternative]),
        default=nc.BootAlternative.network.value,
    )
