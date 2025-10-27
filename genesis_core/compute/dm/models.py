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
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.dm import types_network as types_net
from restalchemy.dm import filters as dm_filters
from restalchemy.storage.sql import orm
from gcl_sdk.infra.dm import models as infra_models
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.compute import constants as nc
from genesis_core.common import utils
from genesis_core.common import system
from genesis_core.common.dm import models as cm


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
        return bool(self.driver_spec)

    @classmethod
    def default_hw_pool(cls) -> "MachinePool" | None:
        """Get the default pool for HW machines if exists.

        The method returns the default pool if only a pool
        with required parameters exists and there are not
        other pools with similar parameters.
        """
        return cls.objects.get_one_or_none(
            filters={
                "machine_type": dm_filters.EQ(nc.NodeType.HW.value),
                "driver_spec": dm_filters.EQ("{}"),
                "status": dm_filters.EQ(nc.MachinePoolStatus.ACTIVE.value),
            },
        )

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


class NodeSet(
    infra_models.NodeSet,
    ua_models.InstanceWithDerivativesMixin,
):
    __tablename__ = "compute_sets"

    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: sys_uuid.uuid4(),
    )

    status = properties.property(
        types.Enum([s.value for s in nc.NodeStatus]),
        default=nc.NodeStatus.NEW.value,
    )


class Node(
    infra_models.Node,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "nodes"
    __jsonfields__ = ["default_network"]

    uuid = properties.property(
        types.UUID(),
        read_only=True,
        id_property=True,
        default=lambda: sys_uuid.uuid4(),
    )

    status = properties.property(
        types.Enum([s.value for s in nc.NodeStatus]),
        default=nc.NodeStatus.NEW.value,
    )

    node_set = properties.property(types.AllowNone(types.UUID()), default=None)

    def insert(self, session=None):
        super().insert(session=session)

        for policy in self.placement_policies:
            allocation = FlatPlacementPolicyAllocation(
                node=self.uuid,
                policy=policy,
            )
            allocation.insert(session=session)

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

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of Node target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "name",
                "cores",
                "ram",
                "root_disk_size",
                "node_type",
                "image",
                "project_id",
                "node_set",
                "placement_policies",
            )
        )


class Machine(
    cm.ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin
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


class Volume(
    cm.ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin
):
    __tablename__ = "node_volumes"

    node = properties.property(types.AllowNone(types.UUID()))
    size = properties.property(types.Integer(min_value=1, max_value=1000000))
    boot = properties.property(types.Boolean(), default=True)
    label = properties.property(
        types.AllowNone(types.String(max_length=127)), default=None
    )
    # TODO(g.melikov): DON'T USE! Should be dropped.
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


class UnscheduledNode(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "unscheduled_nodes"

    node = relationships.relationship(
        Node,
        prefetch=True,
        required=True,
    )


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
    cm.ModelWithFullAsset,
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
    cm.ModelWithFullAsset,
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
    ip_discovery_range = properties.property(
        types.AllowNone(IPRange()),
        default=None,
    )

    dns_servers = properties.property(
        types.AllowNone(
            types.TypedList(types.String(min_length=1, max_length=128))
        ),
        default=lambda: [],
    )
    routers = properties.property(
        types.AllowNone(
            types.TypedList(
                types.SchemeDict(
                    {
                        "to": types_net.Network(),
                        "via": types_net.IPAddress(),
                    }
                )
            )
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

    @property
    def ip_discovery_range_pair(
        self,
    ) -> tp.Tuple[netaddr.IPAddress, netaddr.IPAddress] | None:
        if self.ip_discovery_range is None:
            return None

        return (
            netaddr.IPAddress(self.ip_discovery_range.first),
            netaddr.IPAddress(self.ip_discovery_range.last),
        )


class Port(
    cm.ModelWithFullAsset, orm.SQLStorableMixin, models.SimpleViewMixin
):
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

    @classmethod
    def get_vm_nodes(cls):
        return cls.objects.get_all(
            filters={
                "node_type": dm_filters.EQ(nc.NodeType.VM.value),
            }
        )


class HWNodeWithoutPorts(models.ModelWithUUID, orm.SQLStorableMixin):
    __tablename__ = "compute_hw_nodes_without_ports"

    machine = properties.property(types.UUID())
    node = properties.property(types.UUID())
    iface = properties.property(types.UUID())

    @classmethod
    def get_nodes(cls):
        return cls.objects.get_all()


class Interface(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    models.SimpleViewMixin,
    orm.SQLStorableMixin,
):
    __tablename__ = "compute_net_interfaces"

    machine = properties.property(types.UUID())
    mac = properties.property(types.Mac(), required=True)
    ipv4 = properties.property(
        types.AllowNone(types_net.IPAddress()), default=None
    )
    mask = properties.property(
        types.AllowNone(types_net.IPAddress()),
        default=None,
    )
    mtu = properties.property(
        types.Integer(min_value=1, max_value=65536), default=1500
    )

    @classmethod
    def from_system(cls) -> tp.List["Interface"]:
        ifaces = []
        system_uuid = system.system_uuid()
        for iface in system.get_ifaces():
            # TODO(akremenetsky): Support multiple IPv4 addresses for
            # an interface
            uuid = sys_uuid.uuid5(system_uuid, iface["mac"])
            ipv4 = next(iter(iface["ipv4_addresses"]), None)
            mask = next(iter(iface["masks"]), None)
            ifaces.append(
                cls(
                    uuid=uuid,
                    name=iface["name"],
                    mac=iface["mac"],
                    ipv4=ipv4,
                    mask=mask,
                    mtu=iface["mtu"],
                )
            )

        return ifaces


# Placement


class PlacementDomain(
    models.SimpleViewMixin,
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "compute_placement_domains"


class PlacementZone(
    models.SimpleViewMixin,
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "compute_placement_zones"

    domain = relationships.relationship(
        PlacementDomain,
        prefetch=True,
        required=True,
    )


class PlacementPolicy(
    models.SimpleViewMixin,
    cm.ModelWithFullAsset,
    orm.SQLStorableMixin,
):
    __tablename__ = "compute_placement_policies"

    domain = relationships.relationship(
        PlacementDomain,
        prefetch=True,
    )
    zone = relationships.relationship(
        PlacementZone,
        prefetch=True,
    )
    kind = properties.property(
        types.Enum([p.value for p in nc.PlacementPolicyKind]),
        required=True,
        default=nc.PlacementPolicyKind.SOFT_ANTI_AFFINITY.value,
    )


class FlatPlacementPolicyAllocation(
    models.ModelWithUUID,
    models.SimpleViewMixin,
    orm.SQLStorableMixin,
):
    __tablename__ = "compute_placement_policy_allocations"

    node = properties.property(
        types.UUID(),
        required=True,
    )
    policy = properties.property(
        types.UUID(),
        required=True,
    )


class PlacementPolicyAllocation(FlatPlacementPolicyAllocation):
    node = relationships.relationship(
        Node,
        prefetch=True,
        required=True,
    )
    policy = relationships.relationship(
        PlacementPolicy,
        prefetch=True,
        required=True,
    )
