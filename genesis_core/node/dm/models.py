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

import random
import typing as tp
import netaddr
import uuid as sys_uuid

import netaddr
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_network as types_net
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


class CastToBaseMixin:
    __cast_filels__ = None

    def cast_to_base(self) -> models.SimpleViewMixin:
        # Convert to simple view without relations
        fields = self.__cast_filels__ or tuple(
            self.properties.properties.keys()
        )
        view = self.dump_to_simple_view(skip=fields)

        # Translate relations into uuid
        for relation in fields:
            value = getattr(self, relation)
            if value is not None:
                view[relation] = value.uuid

        # Find base class
        base_class = None
        for base in self.__class__.__bases__:
            if base != CastToBaseMixin:
                base_class = base
                break
        else:
            raise RuntimeError(
                f"Failed to find base class for {self.__class__}"
            )

        return base_class.restore_from_simple_view(**view)


class IPRange(types.BaseType):
    SEPARATOR = "-"

    def __init__(self, **kwargs):
        super(IPRange, self).__init__(openapi_type="string", **kwargs)

    def validate(self, value):
        return isinstance(value, netaddr.IPRange)

    def to_simple_type(self, value):
        return str(value)

    def from_simple_type(self, value):
        return netaddr.IPRange(*value.split(self.SEPARATOR))

    def from_unicode(self, value):
        return self.from_simple_type(value)


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


class Node(
    ModelWithFullAsset,
    orm.SQLStorableWithJSONFieldsMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "nodes"
    __jsonfields__ = ["default_network"]

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
    default_network = properties.property(types.Dict(), default=lambda: {})

    def update_default_network(self, port: Port) -> None:
        self.default_network = {
            "subnet": str(port.subnet),
            "port": str(port.uuid),
            "ipv4": str(port.ipv4) if port.ipv4 else None,
            "target_ipv4": str(port.target_ipv4) if port.target_ipv4 else None,
            "mask": str(port.mask) if port.mask else None,
            "mac": port.mac,
        }
        self.update()


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

    # Actual image of the machine
    image = properties.property(
        types.AllowNone(types.String(max_length=255)), default=None
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


class Network(
    ModelWithFullAsset,
    orm.SQLStorableWithJSONFieldsMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "compute_networks"
    __jsonfields__ = ["driver_spec"]
    __driver_map__ = {}

    driver_spec = properties.property(types.Dict(), default=lambda: {})

    def load_driver(self) -> tp.Type["AbstractNetworkDriver"]:
        driver_key = str(self.driver_spec)

        if driver_key in self.__driver_map__:
            return self.__driver_map__[driver_key]

        ep_group = utils.load_group_from_entry_point(nc.EP_NETWORK_DRIVERS)
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


class Subnet(
    ModelWithFullAsset,
    orm.SQLStorableWithJSONFieldsMixin,
    models.SimpleViewMixin,
):
    __tablename__ = "compute_subnets"
    __jsonfields__ = ["dns_servers", "routers"]

    network = properties.property(types.UUID())
    cidr = properties.property(
        types_net.Network(),
        required=True,
        read_only=True,
    )
    ip_range = properties.property(
        types.AllowNone(IPRange()),
        default=None,
    )
    dhcp = properties.property(
        types.Boolean(),
        default=True,
    )

    dns_servers = properties.property(
        types.AllowNone(
            types.TypedList(types.String(min_length=1, max_length=128))
        ),
        default=lambda: [],
    )
    routers = properties.property(
        types.AllowNone(
            types.TypedList(types.String(min_length=1, max_length=128))
        ),
        default=lambda: [],
    )
    next_server = properties.property(
        types.String(max_length=256), default="127.0.0.1"
    )

    def port(
        self,
        target_ipv4: netaddr.IPAddress | None = None,
        ipv4: netaddr.IPAddress | None = None,
        target_mask: netaddr.IPAddress | None = None,
        mask: netaddr.IPAddress | None = None,
        mac: str | None = None,
        node_uuid: sys_uuid.UUID | None = None,
        machine_uuid: sys_uuid.UUID | None = None,
        project_id: str | None = None,
    ) -> Port:
        port = Port(
            subnet=self.uuid,
            target_ipv4=target_ipv4,
            target_mask=target_mask,
            node=node_uuid,
            machine=machine_uuid,
            mac=mac,
            ipv4=ipv4,
            mask=mask,
            project_id=project_id or self.project_id,
        )
        return port

    @property
    def ip_range_pair(
        self,
    ) -> tp.Tuple[netaddr.IPAddress, netaddr.IPAddress] | None:
        if self.ip_range is None:
            return None

        return (
            netaddr.IPAddress(self.ip_range.first),
            netaddr.IPAddress(self.ip_range.last),
        )


class Port(ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin):
    __tablename__ = "compute_ports"

    subnet = properties.property(types.UUID())

    node = properties.property(types.AllowNone(types.UUID()), default=None)
    machine = properties.property(types.AllowNone(types.UUID()), default=None)

    interface = properties.property(
        types.AllowNone(types.String(min_length=1, max_length=32)),
        default=None,
    )
    target_ipv4 = properties.property(
        types.AllowNone(types_net.IPAddress()),
        default=None,
    )
    target_mask = properties.property(
        types.AllowNone(types_net.IPAddress()),
        default=None,
    )
    ipv4 = properties.property(
        types.AllowNone(types_net.IPAddress()), default=None
    )
    mask = properties.property(
        types.AllowNone(types_net.IPAddress()),
        default=None,
    )
    mac = properties.property(types.AllowNone(types.Mac()), default=None)
    status = properties.property(
        types.Enum([s.value for s in nc.PortStatus]),
        default=nc.PortStatus.NEW.value,
    )

    @staticmethod
    def generate_mac(virtual_machine: bool = True) -> str:
        octets = tuple(random.randint(0, 255) for _ in range(5))

        if virtual_machine:
            return "52:54:00:%02x:%02x:%02x" % octets[2:]

        return "a9:%02x:%02x:%02x:%02x:%02x" % octets


class NodeWithoutPorts(Node):
    __tablename__ = "compute_nodes_without_ports"

    @classmethod
    def get_nodes(cls):
        return cls.objects.get_all()
