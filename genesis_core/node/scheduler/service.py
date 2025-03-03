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
import random
import typing as tp

from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node.dm import models
from genesis_core.node import constants as nc

LOG = logging.getLogger(__name__)


class NodeSchedulerService(basic.BasicService):

    def _get_unscheduled_nodes(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> models.UnscheduledNode:
        """Get all unscheduled nodes."""
        return models.UnscheduledNode.objects.get_all(limit=limit)

    def _get_unscheduled_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> models.MachinePool:
        """Get all unscheduled pools."""
        return models.MachinePool.objects.get_all(
            filters={"agent": dm_filters.Is(None)},
            limit=limit,
        )

    def _get_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.MachinePool]:
        """Get all active pools."""
        return models.MachinePool.objects.get_all(
            filters={
                "status": dm_filters.EQ(nc.MachinePoolStatus.ACTIVE.value),
                "machine_type": dm_filters.EQ(nc.NodeType.VM.value),
                "agent": dm_filters.IsNot(None),
                "driver_spec": dm_filters.NE("{}"),
            },
            limit=limit,
        )

    def _build_vm(
        self, node: models.UnscheduledNode, pool: models.MachinePool
    ) -> models.Machine:
        machine_uuid = node.uuid
        machine = models.Machine(
            uuid=machine_uuid,
            firmware_uuid=machine_uuid,
            pool=pool.uuid,
            name=node.name,
            cores=node.cores,
            ram=node.ram,
            node=node.uuid,
            project_id=node.project_id,
            machine_type=nc.NodeType.VM.value,
            status=nc.MachineStatus.SCHEDULED.value,
        )
        return machine

    def _schedule_nodes(self):
        unsheduled = self._get_unscheduled_nodes()
        if not unsheduled:
            LOG.debug("Nothing to schedule, no unscheduled nodes")
            return

        # TODO(akremenetsky): Implement for HWs
        # TODO(akremenetsky): Implement based on real pool resources
        # The simplest implementation is to schedule to a random pool
        pools = self._get_pools()
        if not pools:
            nodes = (node.uuid for node in unsheduled)
            LOG.warning("No pools found to schedule nodes %s", nodes)
            return

        for node in unsheduled:
            pool = random.choice(pools)

            # Scheduler performs a builder role so far
            try:
                machine = self._build_vm(node, pool)
                machine.insert()
                LOG.info(
                    "The node %s scheduled to %s pool", node.uuid, pool.uuid
                )
            except Exception:
                LOG.exception("Error building node %s", node.uuid)

    def _schedule_pools(self):
        unsheduled = self._get_unscheduled_pools()
        if not unsheduled:
            LOG.debug("Nothing to schedule, no unscheduled pools")
            return

        # The simplest implementation is to schedule to a random machine agent
        agents = models.MachineAgent.all_active()
        if not agents:
            pools = [pool.uuid for pool in unsheduled]
            LOG.warning("No machine agents found to schedule pools %s", pools)
            return

        for pool in unsheduled:
            agent = random.choice(agents)

            try:
                pool.agent = agent.uuid
                pool.update()
                LOG.info(
                    "The pool %s scheduled to machine agent %s",
                    pool.uuid,
                    agent.uuid,
                )
            except Exception:
                LOG.exception("Error scheduling pool %s", pool.uuid)

    def _iteration(self):
        with contexts.Context().session_manager():
            # Pools
            try:
                self._schedule_pools()
            except Exception:
                LOG.exception("Error scheduling pools:")

            # Nodes
            try:
                self._schedule_nodes()
            except Exception:
                LOG.exception("Error scheduling nodes:")
