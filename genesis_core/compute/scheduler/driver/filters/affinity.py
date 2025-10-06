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

from restalchemy.dm import filters as dm_filters

from genesis_core.compute.dm import models
from genesis_core.compute.scheduler.driver import base


class DummySoftAntiAffinityFilter(base.MachinePoolAbstractFilter):

    def filter(
        self,
        node: base.NodeBundle,
        pools: tp.List[base.MachinePoolBundle],
    ) -> tp.Iterable[base.MachinePoolBundle]:
        """Filter out pools that are not suitable for the node."""
        # Get all policies for the node
        allocations = models.PlacementPolicyAllocation.objects.get_all(
            filters={
                "node": dm_filters.EQ(node.node.uuid),
            }
        )

        # If no policies, we don't have any constraints
        if not allocations:
            return pools

        nodes_in_allocations = (
            models.PlacementPolicyAllocation.objects.get_all(
                filters={
                    "policy": dm_filters.In(a.policy for a in allocations),
                }
            )
        )

        # TODO(akremenetsky): So far all policies are soft anti affinity
        # Other policies are not supported.
        machines_in_policy = models.Machine.objects.get_all(
            filters={
                "node": dm_filters.In(
                    a.node.uuid
                    for a in nodes_in_allocations
                    if a.node.uuid != node.node.uuid
                ),
            }
        )

        avail_pools = {p.pool.uuid for p in pools} - {
            m.pool for m in machines_in_policy
        }

        # For soft anti affinity we allow to schedule machine to any pool
        # if there are no free pools
        if not avail_pools:
            return pools

        return tuple(p for p in pools if p.pool.uuid in avail_pools)
