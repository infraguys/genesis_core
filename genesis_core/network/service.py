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
import netaddr
import collections
import typing as tp

from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node.dm import models
from genesis_core.network.dm import models as net_models
from genesis_core.network.driver import base as net_base
from genesis_core.network import ipam as net_ipam

LOG = logging.getLogger(__name__)
TARGET_IP_KEY = "target_ipv4"


class NetworkService(basic.BasicService):

    def _get_new_vm_nodes(self) -> tp.List[models.NodeWithoutPorts]:
        return models.NodeWithoutPorts.get_vm_nodes()

    def _get_new_hw_ports(
        self, subnets: tp.Iterable[net_models.Subnet]
    ) -> tp.List[net_models.Port]:
        ports = []
        nodes = net_models.HWNodeWithoutPorts.get_nodes()

        if not nodes:
            return ports

        # Prepare ports for HW nodes.
        # Need to detect the corresponding subnets
        for node in nodes:
            for subnet in subnets:
                if node.iface.ipv4 in subnet.cidr:
                    # Create ports for HW nodes
                    port = net_models.Port(
                        subnet=subnet,
                        mac=node.iface.mac,
                        project_id=subnet.project_id,
                        node=node.node,
                        machine=node.machine,
                        mask=subnet.cidr.netmask,
                    )
                    ports.append(port)

        return ports

    def _get_subnet_map(
        self,
    ) -> tp.Dict[net_models.Subnet : tp.List[net_models.Port]]:
        # TODO(akremenetsky): Take all subnets so far.
        # This snippet will be reworked.
        subnets = net_models.Subnet.objects.get_all()
        ports = net_models.Port.objects.get_all(
            filters={
                "subnet": dm_filters.In(
                    [str(subnet.uuid) for subnet in subnets]
                ),
            }
        )

        port_subnet_map = collections.defaultdict(list)
        for port in ports:
            port_subnet_map[port.subnet.uuid].append(port)

        # A subnet can be created without any ports. In this case
        # we create an empty list for this subnet so that the
        # actualization logic will work correctly.
        subnet_map = {}
        for subnet in subnets:
            if subnet.uuid in port_subnet_map:
                subnet_map[subnet] = port_subnet_map[subnet.uuid]
            else:
                subnet_map[subnet] = []

        return subnet_map

    def _build_network_map(
        self, subnet_map: tp.Dict[net_models.Subnet : tp.List[net_models.Port]]
    ) -> tp.DefaultDict[
        models.Network : tp.Dict[net_models.Subnet : tp.List[net_models.Port]]
    ]:
        network_map = collections.defaultdict(dict)

        for subnet in subnet_map.keys():
            network_map[subnet.network][subnet] = subnet_map[subnet]

        return network_map

    def _actualize_network(
        self,
        network: models.Network,
        subnet_map: tp.Dict[net_models.Subnet : tp.List[net_models.Port]],
    ) -> None:
        driver: net_base.AbstractNetworkDriver = network.load_driver()
        actual_subnets = {s.uuid: s for s in driver.list_subnets()}
        target_subnets = {s.uuid: s for s in subnet_map.keys()}

        # Create subnets
        for uuid in target_subnets.keys() - actual_subnets.keys():
            subnet = target_subnets[uuid]
            try:
                driver.create_subnet(subnet.cast_to_base())
            except Exception:
                LOG.exception("Error creating subnet %s", subnet.uuid)

        # Delete subnets
        for uuid in actual_subnets.keys() - target_subnets.keys():
            subnet = actual_subnets[uuid]
            try:
                driver.delete_subnet(subnet)
            except Exception:
                LOG.exception("Error deleting subnet %s", subnet.uuid)

        # Actualize subnets
        for uuid in actual_subnets.keys() & target_subnets.keys():
            target_subnet = target_subnets[uuid]
            actual_subnet = actual_subnets[uuid]
            target_ports = subnet_map[target_subnet]

            try:
                self._actualize_subnet(
                    driver,
                    actual_subnet,
                    target_subnet,
                    target_ports,
                )
            except Exception:
                LOG.exception(
                    "Error actualizing subnet %s", actual_subnet.uuid
                )

    def _actualize_subnet(
        self,
        driver: net_base.AbstractNetworkDriver,
        actual_subnet: models.Subnet,
        target_subnet: net_models.Subnet,
        target_ports: tp.List[net_models.Port],
    ) -> None:
        actual_ports = {p.uuid: p for p in driver.list_ports(actual_subnet)}
        target_ports = {p.uuid: p for p in target_ports}

        if (
            target_subnet.cidr != actual_subnet.cidr
            or target_subnet.next_server != actual_subnet.next_server
        ):
            try:
                subnet = driver.update_subnet(target_subnet.cast_to_base())
                target_subnet.cidr = subnet.cidr
                target_subnet.next_server = subnet.next_server
                target_subnet.update()
            except Exception:
                LOG.exception(
                    "Error actualizing subnet %s", actual_subnet.uuid
                )

        # Create ports
        ports = tuple(
            target_ports[u].cast_to_base()
            for u in target_ports.keys() - actual_ports.keys()
        )
        try:
            if ports:
                ports = driver.create_ports(ports)
        except Exception:
            LOG.exception("Error creating ports: %s", ports)
            ports = tuple()

        for p in ports:
            target_port = target_ports[p.uuid]
            target_port.status = p.status
            target_port.ipv4 = p.ipv4
            target_port.mask = p.mask
            target_port.mac = p.mac
            target_port.interface = p.interface

            try:
                # Update `default_network` for the node
                if not "port" in target_port.node.default_network:
                    target_port.node.update_default_network(p)
                target_port.update()
            except Exception:
                LOG.exception("Error creating port %s", target_port.uuid)

        # Delete ports
        ports = tuple(
            actual_ports[u] for u in actual_ports.keys() - target_ports.keys()
        )
        try:
            if ports:
                driver.delete_ports(ports)
        except Exception:
            LOG.exception("Error creating ports: %s", ports)
            ports = tuple()

        # Actualize ports
        for uuid in actual_ports.keys() & target_ports.keys():
            target_port = target_ports[uuid]
            actual_port = actual_ports[uuid]

            # Actualize a small set of fields so far
            if (
                target_port.ipv4 != actual_port.ipv4
                or target_port.mask != actual_port.mask
            ):
                try:
                    driver.update_port(target_port.cast_to_base())
                except Exception:
                    LOG.exception(
                        "Error actualizing port %s", actual_port.uuid
                    )

            # Actualize status
            if (
                target_port.status != actual_port.status
                or target_port.ipv4 != actual_port.ipv4
                or target_port.mask != actual_port.mask
            ):
                target_port.status = actual_port.status
                target_port.ipv4 = actual_port.ipv4
                target_port.mask = actual_port.mask

                try:
                    # Update `default_network` for the node as well
                    if target_port.node.default_network.get("port") == str(
                        target_port.uuid
                    ):
                        target_port.node.update_default_network(actual_port)
                    target_port.update()
                except Exception:
                    LOG.exception(
                        "Unable to actualize status of port %s",
                        actual_port.uuid,
                    )

    def _is_subnet_match(
        self, node: models.NodeWithoutPorts, subnet: net_models.Subnet
    ) -> bool:
        # TODO(akremenetsky): Only single network is supported for now
        return True

    def _allocate_port(
        self,
        node: models.NodeWithoutPorts,
        ipam: net_ipam.Ipam,
        subnet_map: tp.Dict[net_models.Subnet : tp.List[net_models.Port]],
    ) -> net_models.Port:
        # Figure out the correct subnet
        for subnet, ports in subnet_map.items():
            if self._is_subnet_match(node, subnet):
                break
        else:
            raise ValueError("No suitable subnet found for node %s", node.uuid)

        target_ip = None
        if node.default_network.get(TARGET_IP_KEY):
            target_ip = netaddr.IPAddress(node.default_network[TARGET_IP_KEY])

        ip = ipam.allocate_ip(subnet, target_ip)
        mask = subnet.cidr.netmask
        target_mask = mask if target_ip else None
        port = models.Port(
            target_ipv4=target_ip,
            target_mask=target_mask,
            ipv4=ip,
            mask=mask,
            node=node.uuid,
            mac=models.Port.generate_mac(),
            project_id=node.project_id,
            subnet=subnet.uuid,
        )
        net_port = net_models.Port.restore_from_simple_view(
            **port.dump_to_simple_view()
        )

        subnet_map[subnet].append(net_port)

        return net_port

    def _iteration(self) -> None:
        ipam = None

        with contexts.Context().session_manager():
            new_vm_nodes = self._get_new_vm_nodes()
            subnet_map = self._get_subnet_map()
            new_hw_ports = self._get_new_hw_ports(subnet_map.keys())
            network_map = self._build_network_map(subnet_map)

            # There are new nodes. Allocate ports to them.
            for node in new_vm_nodes:
                # Initialize ipam if needed
                if ipam is None:
                    ipam = net_ipam.Ipam(subnet_map)

                # Try to allocate a port for the new node
                try:
                    port = self._allocate_port(node, ipam, subnet_map)
                    port.insert()
                except ValueError:
                    LOG.error(
                        "No suitable subnet found for node %s", node.uuid
                    )
                    continue
                except Exception:
                    ipam.deallocate_ip(port.subnet, port.ipv4)
                    LOG.exception(
                        "Error allocating port for node %s", node.uuid
                    )

            # There are new HW ports. Allocate IPs to them.
            for port in new_hw_ports:
                # Initialize ipam if needed
                if ipam is None:
                    ipam = net_ipam.Ipam(subnet_map)
                try:
                    port.ipv4 = ipam.allocate_ip(port.subnet)
                    port.insert()
                    subnet_map[port.subnet].append(port)
                except Exception:
                    LOG.exception(
                        "Error allocating IP for machine %s", port.machine
                    )

            # Actualize ports and subnets on the data plane
            for network, net_subnet_map in network_map.items():
                try:
                    self._actualize_network(network, net_subnet_map)
                except Exception:
                    LOG.exception("Error actualizing network %s", network.uuid)
