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

import pytest
from genesis_core.node.dm import models
from genesis_core.node.scheduler.driver.weighter import relative


class TestSchedulerWeighter:

    @pytest.fixture
    def weighter(self):
        return relative.RelativeCoreRamWeighter()

    @pytest.fixture
    def pools(self):
        return [
            # 50% used
            models.MachinePool(
                all_cores=100, avail_cores=50, all_ram=100000, avail_ram=50000
            ),
            # 20% used
            models.MachinePool(
                all_cores=100, avail_cores=80, all_ram=100000, avail_ram=80000
            ),
            # Fully used
            models.MachinePool(
                all_cores=100, avail_cores=0, all_ram=100000, avail_ram=0
            ),
        ]

    def test_weight_empty_system(self, weighter):
        """Test weighting when the system is empty (no usage)."""
        empty_pools = [
            models.MachinePool(
                all_cores=100,
                avail_cores=100,
                all_ram=100000,
                avail_ram=100000,
            )
        ]
        weights = list(weighter.weight(empty_pools))
        assert len(weights) == 1
        assert weights[0] == 1.0

    def test_weight(self, weighter, pools):
        """Test the weight calculation with different levels of usage."""
        weights = list(weighter.weight(pools))
        assert len(weights) == 3
        # Expect pools with less usage to have a higher weight
        assert weights[1] > weights[0] > weights[2]

    def test_weight_with_overused_pool(self, weighter):
        """Test weighting with a pool that is overused."""
        overused_pools = [
            models.MachinePool(
                all_cores=100, avail_cores=-10, all_ram=100000, avail_ram=-5000
            )
        ]
        weights = list(weighter.weight(overused_pools))
        assert len(weights) == 1

        # Weight for overused pool might be treated as the worst case
        assert weights[0] == 0.0
