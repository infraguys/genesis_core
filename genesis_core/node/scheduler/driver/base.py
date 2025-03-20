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

import abc
import typing as tp


from genesis_core.node.dm import models


class MachinePoolAbstractFilter(abc.ABC):

    @abc.abstractmethod
    def filter(
        self,
        machine: models.Machine,
        pools: tp.List[models.MachinePool],
    ) -> tp.Iterable[models.MachinePool]:
        """Filter out pools that are not suitable for the node."""


class MachinePoolAbstractWeighter(abc.ABC):
    @abc.abstractmethod
    def weight(
        self,
        pools: tp.List[models.MachinePool],
    ) -> tp.Iterable[float]:
        """Assign weights to machine pools.

        Every machine pool gets a weight from range [0, 1].
        1 means the pool is the best for the node.
        0 means the pool is the worst for the node.
        """


class MachineAbstractFilter(abc.ABC):

    def filter(
        self,
        node: models.Node,
        machines: tp.List[models.Machine],
    ) -> tp.Iterable[models.Machine]:
        """Filter out machines that are not suitable for the node."""


class MachineAbstractWeighter(abc.ABC):
    def weight(
        self,
        machines: tp.List[models.MachinePool],
    ) -> tp.Iterable[float]:
        """Assign weights to machines.

        Every machine gets a weight from range [0, 1].
        1 means the machine is the best for the node.
        0 means the machine is the worst for the node.
        """
