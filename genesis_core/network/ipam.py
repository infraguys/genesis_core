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
import uuid as sys_uuid
import typing as tp

from genesis_core.network.dm import models as net_models
from genesis_core.network import exceptions as net_exceptions

LOG = logging.getLogger(__name__)


class IpamNoIPsAvailable(net_exceptions.CGNetException):
    __template__ = "No more IPs available for subnet {subnet}"
    subnet: sys_uuid.UUID


class IpamUndefinedSubnet(net_exceptions.CGNetException):
    __template__ = "Undefined subnet {subnet}"
    subnet: sys_uuid.UUID


class IpamIpNotFound(net_exceptions.CGNetException):
    __template__ = "IP {ip} not found"
    ip: netaddr.IPAddress


class Ipam:

    def __init__(
        self,
        subnet_map: tp.Dict[net_models.Subnet : tp.List[net_models.Port]],
    ) -> None:
        """
        Initialize IPAM with a subnet map.

        subnet_map is a dictionary where key is a subnet object and value is a list of ports
        that are already allocated from this subnet. The ipam will initialize the pool of
        free IPs for each subnet by excluding the allocated IPs from the pool.

        After initialization the ipam is ready to be used for allocating and deallocating
        IPs from the subnets.

        :param subnet_map: a dictionary where key is a subnet object and value is a list of
        ports that are already allocated from this subnet.
        :type subnet_map: Dict[net_models.Subnet, List[net_models.Port]]
        """
        self._pool_map = {}

        # TODO(akremenetsky): No need to calculate the pool for each subnet here,
        # we may do it in a lazy way when it will be required
        for subnet, ports in subnet_map.items():
            self.add_subnet(subnet, ports)

    def add_subnet(
        self, subnet: net_models.Subnet, ports: tp.Iterable[net_models.Port]
    ) -> None:
        self._pool_map[subnet] = self.calculate_pool(subnet, ports)

    def calculate_pool(
        self, subnet: net_models.Subnet, ports: tp.Iterable[net_models.Port]
    ) -> tp.List[tp.Tuple[int, int]]:
        ip_start, ip_end = subnet.cidr[0], subnet.cidr[-1]
        if subnet.ip_range_pair:
            ip_start, ip_end = subnet.ip_range_pair

        pool = [(int(ip_start), int(ip_end))]
        for port in ports:
            if port.ipv4 is not None:
                ip = int(netaddr.IPAddress(port.ipv4))
                self.occupy_ip(ip, pool)

        return pool

    def occupy_ip(
        self,
        address: int,
        address_pool: tp.List[tp.Tuple[int, int]],
    ) -> None:
        for i, (s, e) in enumerate(address_pool):
            if s == e and s == address:
                address_pool.pop(i)
                return
            elif address == s:
                address_pool[i] = (s + 1, e)
                return
            elif address == e:
                address_pool[i] = (s, e - 1)
                return
            elif s < address < e:
                address_pool[i] = (s, address - 1)
                address_pool.insert(i + 1, (address + 1, e))
                return

        raise IpamIpNotFound(ip=netaddr.IPAddress(address))

    def allocate_ip(
        self,
        subnet: net_models.Subnet,
        target_ip: netaddr.IPAddress | None = None,
    ) -> netaddr.IPAddress:
        if subnet not in self._pool_map:
            raise IpamUndefinedSubnet(subnet=str(subnet.uuid))

        address_pool = self._pool_map[subnet]

        if len(address_pool) == 0:
            raise IpamNoIPsAvailable(subnet=str(subnet.uuid))

        # Try to occupy the target IP
        if target_ip is not None:
            self.occupy_ip(int(target_ip), address_pool)
            return target_ip

        # Take a firt available IP address
        start, end = address_pool[0]
        if start == end:
            address_pool.pop(0)
        else:
            address_pool[0] = (start + 1, end)

        return netaddr.IPAddress(start)

    def deallocate_ip(
        self,
        subnet: net_models.Subnet,
        address: netaddr.IPAddress,
    ) -> None:
        if subnet not in self._pool_map:
            raise IpamUndefinedSubnet(subnet=str(subnet.uuid))

        address_pool = self._pool_map[subnet]

        address = int(address)

        for i, (s, e) in enumerate(address_pool):
            if address < s - 1:
                address_pool.insert(i, (address, address))
                return
            elif address == s - 1:
                address_pool[i] = (s - 1, e)
                return
            elif address == e + 1:
                address_pool[i] = (s, e + 1)

                # Merging
                if i + 1 < len(address_pool):
                    next_start, next_end = address_pool[i + 1]
                    if next_start - 1 == address:
                        address_pool[i] = (s, next_end)
                        address_pool.pop(i + 1)
                return
            elif s < address < e:
                LOG.warning("IP %s is not allocated", address)
                return

        address_pool.append((address, address))
