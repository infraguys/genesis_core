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
import typing as tp

from genesis_core.compute.scheduler.driver import base


class CoresRamAvailableFilter(base.MachinePoolAbstractFilter):
    def filter(
        self,
        node: base.NodeBundle,
        pools: tp.List[base.MachinePoolBundle],
    ) -> tp.Iterable[base.MachinePoolBundle]:
        """Filter out pools that are not suitable for the node."""

        node = node.node

        return tuple(
            p
            for p in pools
            if p.pool.avail_cores >= node.cores and p.pool.avail_ram >= node.ram
        )


class HWCoresRamAvailableFilter(base.MachineAbstractFilter):
    def filter(
        self,
        node: base.NodeBundle,
        machines: tp.List[base.MachineBundle],
    ) -> tp.Iterable[base.MachineBundle]:
        """Filter out machines that are not suitable for the node."""

        node = node.node

        return tuple(
            m
            for m in machines
            if m.machine.cores >= node.cores and m.machine.ram >= node.ram
        )
