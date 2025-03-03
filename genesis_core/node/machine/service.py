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
import uuid as sys_uuid
import typing as tp
from collections import defaultdict

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node import constants as nc
from genesis_core.common import utils
from genesis_core.node.dm import models as models
from genesis_core.node.machine.pool.driver import base as pool_driver


LOG = logging.getLogger(__name__)
DEF_MACHINE_AGENT_NAME = "machine-agent"


class MachineAgentService(basic.BasicService):

    def __init__(
        self,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
        agent_uuid: sys_uuid.UUID | None = None,
    ):
        super().__init__(iter_min_period, iter_pause)
        self._agent_uuid = agent_uuid or self._calculate_agent_uuid()

    def _calculate_agent_uuid(self) -> sys_uuid.UUID:
        return sys_uuid.uuid5(utils.node_uuid(), DEF_MACHINE_AGENT_NAME)

    def _get_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.Dict[sys_uuid.UUID, models.MachinePool]:
        return {
            p.uuid: p
            for p in models.MachinePool.objects.get_all(
                filters={
                    "agent": dm_filters.EQ(str(self._agent_uuid)),
                },
                limit=limit,
            )
        }

    def _get_machines(
        self, pools: tp.Dict[sys_uuid.UUID, models.MachinePool]
    ) -> tp.Dict[models.MachinePool, models.Machine]:
        machines: tp.List[models.Machine] = models.Machine.objects.get_all(
            filters={
                "pool": dm_filters.In((str(p.uuid) for p in pools.values())),
            },
        )
        _map = defaultdict(list)
        for m in machines:
            _map[pools[m.pool]].append(m)
        return _map

    def _actualize_pool(
        self,
        pool: models.MachinePool,
        target_machines: tp.List[models.Machine],
    ) -> None:
        if not pool.has_driver:
            LOG.debug("Pool %s has no driver, skipping", pool.uuid)
            return

        # Try to load the driver for this pool
        driver: pool_driver.AbstractPoolDriver = pool.load_driver()

        # Get all machines for this pool
        actual_machines: tp.List[models.Machine] = driver.list_machines()

        # Delete any machines that are not in the target list
        for machine in set(actual_machines) - set(target_machines):
            try:
                driver.delete_machine(machine)
            except Exception:
                LOG.exception(
                    "Unable to delete machine %s from pool %s",
                    machine.uuid,
                    pool.uuid,
                )

        # Create any machines that are not in the actual list
        for machine in set(target_machines) - set(actual_machines):
            volume = None
            try:
                # TODO(akremenetsky): Get rid of this default volume
                # Temporary add a default volume for the machine
                volume = models.MachineVolume(
                    uuid=sys_uuid.uuid4(),
                    machine=machine.uuid,
                    project_id=machine.project_id,
                    size=15,
                )
                volume = driver.create_volume(volume)
                driver.create_machine(machine, [volume])
            except Exception:
                if volume:
                    driver.delete_volume(volume)
                LOG.exception(
                    "Unable to create machine %s in pool %s",
                    machine.uuid,
                    pool.uuid,
                )

        # Actualize any machines that are in both lists
        pending_actualization = (
            (t, a)
            for a in actual_machines
            for t in target_machines
            if a.uuid == t.uuid
        )
        for target_machine, actual_machine in pending_actualization:
            try:
                driver.actualize_machine(target_machine, actual_machine)
            except Exception:
                LOG.exception(
                    "Unable to actualize machine %s in pool %s",
                    target_machine.uuid,
                    pool.uuid,
                )

    def _setup(self):
        # Actually all actions should be done via HTTP requests
        # but for the first implementation we just create the agent
        agent = models.MachineAgent(
            uuid=self._agent_uuid,
            name=DEF_MACHINE_AGENT_NAME,
            status=nc.MachineAgentStatus.ACTIVE.value,
        )
        try:
            agent.insert()
        except ra_exceptions.ConflictRecords:
            # The agent is already created
            pass

    def _iteration(self):
        with contexts.Context().session_manager():
            # Get all pools for this agent and machines on them
            pools = self._get_pools()
            machine_map = self._get_machines(pools)
            for pool in pools.values():
                machines = machine_map.get(pool, [])
                try:
                    self._actualize_pool(pool, machines)
                except Exception:
                    LOG.exception(
                        "Unable to actualize pool %s with machines %s",
                        pool.uuid,
                        machines,
                    )
