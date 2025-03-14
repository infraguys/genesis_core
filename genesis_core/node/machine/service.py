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
import itertools
from collections import defaultdict

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node import constants as nc
from genesis_core.common import utils
from genesis_core.node.dm import models as models
from genesis_core.node.machine.dm import models as machine_models
from genesis_core.node.machine.pool.driver import exceptions as pool_exceptions
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

    def _is_building(self, machine: machine_models.Machine) -> bool:
        return machine.build_status != nc.MachineBuildStatus.READY

    def _actualize_pool_state(
        self,
        pool: models.MachinePool,
        actual_machines: tp.List[models.Machine],
    ) -> None:
        cores = sum(m.cores for m in actual_machines)
        ram = sum(m.ram for m in actual_machines)

        avail_cores = pool.all_cores - cores
        avail_ram = pool.all_ram - ram

        if avail_cores != pool.avail_cores or avail_ram != pool.avail_ram:
            pool.avail_cores = avail_cores
            pool.avail_ram = avail_ram
            pool.update()
            LOG.info(
                "The pool %s actualized cores %s and ram %s",
                pool.uuid,
                avail_cores,
                avail_ram,
            )

    def _get_pools(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.MachinePool]:
        return models.MachinePool.objects.get_all(
            filters={
                "agent": dm_filters.EQ(str(self._agent_uuid)),
            },
            limit=limit,
        )

    def _get_machines(
        self, pools: tp.List[models.MachinePool]
    ) -> tp.DefaultDict[models.MachinePool, tp.List[machine_models.Machine]]:
        machines = machine_models.Machine.objects.get_all(
            filters={
                "pool": dm_filters.In((str(p.uuid) for p in pools)),
            },
        )
        _map = defaultdict(list)
        for m in machines:
            _map[m.pool].append(m)
        return _map

    def _get_volumes(
        self, machines: tp.Iterable[machine_models.Machine]
    ) -> tp.Dict[machine_models.Machine, tp.List[models.MachineVolume]]:
        machines = tuple(machines)
        node_uuids = tuple(str(m.node.uuid) for m in machines if m.node)

        volumes = models.MachineVolume.objects.get_all(
            filters={"node": dm_filters.In(node_uuids)},
        )
        _raw_map = defaultdict(list)
        for v in volumes:
            _raw_map[v.machine].append(v)

        # Every machine gets a list of volumes guaranteed even though
        # if there are no volumes.
        _map = defaultdict(list)
        for m in machines:
            _map[m] = _raw_map[m.uuid]

        return _map

    def _create_volumes(
        self,
        driver: pool_driver.AbstractPoolDriver,
        volumes: tp.Iterable[models.MachineVolume],
    ) -> None:
        for v in volumes:
            try:
                driver.create_volume(v)
            except pool_exceptions.VolumeAlreadyExistsError:
                # Do nothing the volume is already created
                pass

    def _actualize_machine(
        self,
        driver: pool_driver.AbstractPoolDriver,
        target_machine: machine_models.Machine,
        actual_machine: models.Machine,
    ) -> None:
        # FIXME(akremenetsky): It's not obvious what to do in that case
        # since it's not obvious which fields are target state and which actual.
        # Rethink this moment when baremetal will be implemented
        if target_machine.node is None:
            return

        if target_machine.node.cores != actual_machine.cores:
            driver.set_machine_cores(actual_machine, target_machine.node.cores)
            LOG.info("Actualized cores for machine %s", target_machine.uuid)

        if target_machine.node.ram != actual_machine.ram:
            driver.set_machine_ram(actual_machine, target_machine.node.ram)
            LOG.info("Actualized ram for machine %s", target_machine.uuid)

        # Actualize image only for flashed machines
        if nc.BootAlternative[target_machine.boot].boot_from_hd:
            if target_machine.node.image != target_machine.image:
                target_machine.boot = nc.BootAlternative.network.value
                target_machine.update()

                # NOTE(akremenetsky): It's maybe a potential problem if the
                # method throws an exception but this part should be moved
                # into core agent so it's ok as a temporary solution.
                driver.reset_machine(actual_machine)
                LOG.info(
                    "Started actualizing image for machine %s",
                    target_machine.uuid,
                )

    def _actualize_pool(
        self,
        pool: models.MachinePool,
        target_machines: tp.List[machine_models.Machine],
        target_volumes: tp.Dict[machine_models.Machine, models.MachineVolume],
    ) -> None:
        if not pool.has_driver:
            LOG.debug("Pool %s has no driver, skipping", pool.uuid)
            return

        target_machines = {m.uuid: m for m in target_machines}

        # Try to load the driver for this pool
        driver: pool_driver.AbstractPoolDriver = pool.load_driver()

        # Get all machines for this pool
        # NOTE(akremenetsky): Please note that target and actual machines have
        # different types.
        actual_machines: tp.Dict[sys_uuid.UUID, models.Machine] = {
            m.uuid: m for m in driver.list_machines()
        }

        self._actualize_pool_state(pool, actual_machines.values())

        # Delete any machines that are not in the target list
        for uuid in set(actual_machines.keys()) - set(target_machines.keys()):
            machine = actual_machines[uuid]
            try:
                driver.delete_machine(machine)
            except Exception:
                LOG.exception(
                    "Unable to delete machine %s from pool %s",
                    machine.uuid,
                    pool.uuid,
                )

        # Create any machines that are not in the actual list
        for uuid in set(target_machines.keys()) - set(actual_machines.keys()):
            machine = target_machines[uuid]
            # Skip machines that are not ready. They are building and
            # will be ready a little bit later.
            if self._is_building(machine):
                LOG.debug("Machine %s is not ready, skipping", machine.uuid)
                continue

            # First create volumes for the machine
            try:
                self._create_volumes(driver, target_volumes[machine])
            except Exception:
                LOG.exception(
                    "Unable to create volumes for machine %s in pool %s",
                    machine.uuid,
                    pool.uuid,
                )
                continue

            # Everything is ready to create the machine
            try:
                driver.create_machine(
                    machine.cast_to_base(), target_volumes[machine]
                )
            except Exception:
                LOG.exception(
                    "Unable to create machine %s in pool %s",
                    machine.uuid,
                    pool.uuid,
                )

        # Actualize any machines that are in both lists
        for uuid in set(target_machines.keys()) & set(actual_machines.keys()):
            target_machine = target_machines[uuid]
            actual_machine = actual_machines[uuid]
            # Skip machines that are not ready. They are building and
            # will be ready a little bit later.
            if self._is_building(target_machine):
                LOG.debug(
                    "Machine %s is not ready, skipping", target_machine.uuid
                )
                continue

            try:
                # driver.actualize_machine(target_machine, actual_machine)
                self._actualize_machine(driver, target_machine, actual_machine)
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
            pools = self._get_pools(limit=10)
            machine_map = self._get_machines(pools)
            volume_map = self._get_volumes(
                itertools.chain(*machine_map.values())
            )
            for pool in pools:
                machines = machine_map.get(pool, [])
                try:
                    self._actualize_pool(pool, machines, volume_map)
                except Exception:
                    LOG.exception(
                        "Unable to actualize pool %s with machines %s",
                        pool.uuid,
                        machines,
                    )
