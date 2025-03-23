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

from genesis_core.node.dm import models
from genesis_core.node.scheduler.driver import base


class RelativeCoreRamWeighter(base.MachinePoolAbstractWeighter):
    ALMOST_OVERUSED_THRESHOLD = 0.8

    def _usage_ratio(self, pool: models.MachinePool) -> float:
        """Some empirical formula to calculate the usage ratio of the pool."""

        # The pool is overused
        if pool.avail_cores < 0 or pool.avail_ram < 0:
            return 1.0

        # Unable to calculate ratio. Consider the pool overused
        if pool.all_cores == 0 or pool.all_ram == 0:
            return 1.0

        ratios = (
            (pool.all_cores - pool.avail_cores) / pool.all_cores,
            (pool.all_ram - pool.avail_ram) / pool.all_ram,
        )

        # The pool is almost overused
        if any(r > self.ALMOST_OVERUSED_THRESHOLD for r in ratios):
            return max(ratios)

        # Otherwise, all elements have equal weight
        return sum(ratios) / len(ratios)

    def weight(
        self,
        pools: tp.List[models.MachinePool],
    ) -> tp.Iterable[float]:
        """Assign weights to machine pools.

        Every machine pool gets a weight from range [0, 1].
        1 means the pool is the best for the node.
        0 means the pool is the worst for the node.
        """

        # Maximum weight gets a pool with relative maximal cores and ram
        usages = tuple(self._usage_ratio(p) for p in pools)

        # The system is empty, all pools have equal weight
        if sum(usages) == 0:
            return (1 / len(pools) for _ in pools)

        return (1.0 - u / sum(usages) for u in usages)
