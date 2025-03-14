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
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node.dm import models
from genesis_core.node import constants as nc

LOG = logging.getLogger(__name__)
BUILDER_REBALANCE_RATE = 100


class NodeSchedulerService(basic.BasicService):

    def _get_builders(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.Builder]:
        """Get all active builders."""
        return models.Builder.objects.get_all(
            filters={
                "status": dm_filters.EQ(nc.BuilderStatus.ACTIVE.value),
            },
            limit=limit,
        )

    def _get_in_update_machines(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.Machine]:
        """Get all in update machines."""
        return models.Machine.objects.get_all(
            filters={
                "pool": dm_filters.IsNot(None),
                "builder": dm_filters.Is(None),
                "build_status": dm_filters.EQ(
                    nc.MachineBuildStatus.IN_BUILD.value
                ),
            },
            limit=limit,
        )

    def _get_unscheduled_nodes(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.UnscheduledNode]:
        """Get all unscheduled nodes."""
        return models.UnscheduledNode.objects.get_all(limit=limit)

    def _get_unscheduled_machines(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.Machine]:
        """Get all unscheduled machines."""
        return models.Machine.objects.get_all(
            filters={"pool": dm_filters.Is(None)},
            limit=limit,
        )

    def _get_unscheduled_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.MachinePool]:
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
        self,
        node: models.UnscheduledNode,
    ) -> models.Machine:
        machine_uuid = node.uuid
        machine = models.Machine(
            uuid=machine_uuid,
            firmware_uuid=machine_uuid,
            name=node.name,
            cores=node.cores,
            ram=node.ram,
            node=node.uuid,
            project_id=node.project_id,
            machine_type=nc.NodeType.VM.value,
            status=nc.MachineStatus.SCHEDULED.value,
        )
        return machine

    def _build_root_volume(
        self, node: models.UnscheduledNode
    ) -> models.Volume:
        volume_name = "root-volume"
        volume_uuid = sys_uuid.uuid5(node.uuid, volume_name)
        volume = models.Volume(
            uuid=volume_uuid,
            name=volume_name,
            size=node.root_disk_size,
            node=node.uuid,
            project_id=node.project_id,
        )

        return volume

    def _schedule_nodes(self) -> tp.List[models.Machine]:
        machines = []
        unsheduled = self._get_unscheduled_nodes()
        if not unsheduled:
            LOG.debug("Nothing to schedule, no unscheduled nodes")
            return machines

        # TODO(akremenetsky): Implement for HWs
        # TODO(akremenetsky): Implement based on real pool resources
        # The simplest implementation is to schedule to a random pool
        for node in unsheduled:

            # TODO(akremenetsky): It's a builder work. Move to the builder service.
            if node.root_disk_size:
                try:
                    volume = self._build_root_volume(node)
                    volume.insert()
                    LOG.info(
                        "The root volume %s has been created", volume.uuid
                    )
                except ra_exceptions.ConflictRecords:
                    # It's ok, the volume is already created
                    pass

            machines.append(self._build_vm(node))

        return machines

    def _schedule_machines(
        self,
        machines: tp.Iterable[models.Machine],
        builders: tp.Iterable[models.Builder],
    ) -> None:
        if not machines:
            LOG.debug("Nothing to schedule, no unscheduled machines")
            return

        pools = self._get_pools()
        if not pools:
            _machines = (m.uuid for m in machines)
            LOG.warning("No pools found to schedule machines %s", _machines)
            return

        for machine in machines:
            # TODO(akremenetsky): Scheduling based on pipelines
            # TODO(akremenetsky): Look at available resources
            pool = random.choice(pools)
            builder = random.choice(builders)
            machine.pool = pool.uuid
            machine.builder = builder.uuid
            machine.build_status = nc.MachineBuildStatus.IN_BUILD.value
            try:
                machine.save()
                LOG.info(
                    "The machine %s scheduled to %s pool",
                    machine.uuid,
                    pool.uuid,
                )
            except Exception:
                LOG.exception("Error building machine %s", machine.uuid)

    def _schedule_pools(self) -> None:
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

    def _schedule_in_update(self, builders: tp.List[models.Builder]) -> None:
        machines = self._get_in_update_machines()
        if not machines:
            LOG.debug("No in update machines found")
            return

        for machine in machines:
            try:
                builder = random.choice(builders)
                machine.builder = builder.uuid
                machine.update()
                LOG.debug(
                    "The machine %s scheduled to builder %s",
                    machine.uuid,
                    builder.uuid,
                )
            except Exception:
                LOG.exception("Error scheduling machine %s", machine.uuid)

    def _rebalance_builders(self, builders: tp.List[models.Builder]) -> None:
        """Rebalances builders.

        There are two reasons why we would like to rebalance builders:
        1. The build procedure may be pretty long and some machines may
           get stuck waiting for others to be built. A possible solution is
           to rebalance loads between the builders.
        2. Drop "dead" builders. A builder may receive machines
           to build and then become inactive for some reason. In this case,
           the machines will be built indefinitely. To handle this case, we
           need to "drop" all builders from time to time. All active builders
           will register themselves on a new iteration, and all inactive builders
           are removed.
        """
        # Check if the current iteration is a rebalancing point
        if self._iteration_number % BUILDER_REBALANCE_RATE != 0:
            return

        # Delete all builders. They will register on the next iteration.
        for builder in builders:
            builder.delete()
            LOG.debug(
                "The builder %s has been deleted for rebalancing", builder.uuid
            )

    def _iteration(self):
        with contexts.Context().session_manager():
            builders = self._get_builders()
            unscheduled_machines = self._get_unscheduled_machines()

            # Pools
            try:
                self._schedule_pools()
            except Exception:
                LOG.exception("Error scheduling pools:")

            if not builders:
                LOG.warning("No builders found!")
                return

            # Nodes
            try:
                new_machines = self._schedule_nodes()
            except Exception:
                LOG.exception("Error scheduling nodes:")
                new_machines = []

            # Machines. All machines without pools will be scheduled
            machines = set(unscheduled_machines + new_machines)
            try:
                self._schedule_machines(machines, builders)
            except Exception:
                LOG.exception("Error scheduling machines:")

            # Reschedule in update machines.
            # A machine may be updated during its lifetime. For instance,
            # additional volumes will be added or cores will be changes.
            # In such case we need to repeat the scheduling procedure
            # to choose a builder that prepare and reserve all new resources.
            try:
                self._schedule_in_update(builders)
            except Exception:
                LOG.exception("Error scheduling nodes:")

            # There are two reasons why we would like to rebalance builders:
            # 1. The build procedure may be pretty long and some machines may
            #    stuck waiting other will be built. A possible solution is
            #    to rebalance loads between the builders.
            # 2. Drop "dead" builders. A builder may receives machines
            #    to build and then dead for some reason. In this case the
            #    machines will be built infinity time. To handle this case we
            #    need to "drop" all builders time to time. All active builders
            #    will register itself on a new iteration, all dead builders
            #    are removed.
            self._rebalance_builders(builders)
