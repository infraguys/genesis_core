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
import collections
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic

from genesis_core.node.dm import models
from genesis_core.common import utils
from genesis_core.node import constants as nc

LOG = logging.getLogger(__name__)
DEF_BUILDER_NAME = "builder"


class NodeBuilderService(basic.BasicService):

    def __init__(
        self,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
        service_uuid: sys_uuid.UUID | None = None,
    ):
        super().__init__(iter_min_period, iter_pause)
        self._service_uuid = service_uuid or self._calculate_service_uuid()

    def _calculate_service_uuid(self) -> sys_uuid.UUID:
        return sys_uuid.uuid5(utils.node_uuid(), DEF_BUILDER_NAME)

    def _actualize_status(self) -> None:
        try:
            builder = models.Builder.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(str(self._service_uuid)),
                },
            )
        except ra_exceptions.RecordNotFound:
            # Seems the builder has been registered yet
            builder = models.Builder(
                uuid=self._service_uuid,
                status=nc.BuilderStatus.ACTIVE.value,
            )
            builder.insert()

    def _get_pool(self, pool_uuid: sys_uuid.UUID) -> models.MachinePool:
        return models.MachinePool.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(str(pool_uuid)),
            },
        )

    def _get_machines(
        self, limit: int = nc.DEF_SQL_LIMIT
    ) -> tp.List[models.Machine]:
        return models.Machine.objects.get_all(
            filters={
                "builder": dm_filters.EQ(str(self._service_uuid)),
            },
            limit=limit,
        )

    def _get_volumes(
        self, machines: tp.Iterable[models.Machine]
    ) -> tp.Dict[models.Machine, tp.Iterable[models.MachineVolume]]:
        return {}

    def _get_reservations(
        self, machines: tp.Iterable[models.Machine]
    ) -> tp.Dict[models.Machine, tp.List[models.MachinePoolReservations]]:
        reservations = models.MachinePoolReservations.objects.get_all(
            filters={
                "machine": dm_filters.In(tuple(str(m.uuid) for m in machines)),
            },
        )
        reservation_map = collections.defaultdict(list)

        for r in reservations:
            reservation_map[r.machine].append(r)

        # Final map. All reservations for each machine
        return {m: reservation_map[m.uuid] for m in machines}

    def _get_pool_reservations(
        self, pool_uuid: sys_uuid.UUID
    ) -> tp.List[models.MachinePoolReservations]:
        return models.MachinePoolReservations.objects.get_all(
            filters={
                "pool": dm_filters.EQ(str(pool_uuid)),
            },
        )

    def _reschedule_machines(
        self, machine_uuids: tp.List[sys_uuid.UUID]
    ) -> None:
        machines = models.Machine.objects.get_all(
            filters={
                "uuid": dm_filters.In([str(m) for m in machine_uuids]),
            },
        )

        for m in machines:
            m.builder = None
            m.pool = None
            m.build_status = nc.MachineBuildStatus.IN_BUILD.value
            m.update()

    def _mark_machine_ready(self, machine: models.Machine) -> None:
        if (
            machine.build_status != nc.MachineBuildStatus.READY
            or machine.builder is not None
        ):
            machine.build_status = nc.MachineBuildStatus.READY.value
            machine.builder = None
            machine.update()
            LOG.info("Machine %s is ready", machine.uuid)

    def _allocate_pool_reservations(
        self,
        machine: models.Machine,
        volumes: tp.Iterable[models.MachineVolume],
        reservations: tp.List[models.MachinePoolReservations],
    ) -> tp.Tuple[models.MachinePoolReservations]:
        # TODO(akremenetsky): Volume implementation will be added a bit later

        # Check the existing reservations. Perhaps they were
        # reserved on previous iterations.
        # TODO(akremenetsky): Volumes ...
        cores, ram = machine.cores, machine.ram
        for r in reservations:
            cores -= r.cores
            ram -= r.ram

        # Everything is reserved, no need to reserve more
        if cores <= 0 and ram <= 0:
            return tuple()

        # Need to reserve some additional resources
        reservation = models.MachinePoolReservations(
            machine=machine.uuid,
            pool=machine.pool,
            cores=cores,
            ram=ram,
        )
        return (reservation,)

    def _acquire_pool_reservations(
        self,
        pool_uuid: sys_uuid.UUID,
        reservations: tp.Iterable[models.MachinePoolReservations],
    ) -> tp.List[models.MachinePoolReservations]:
        # Try to acquire the reservations
        # TODO(akremenetsky): Acquire lock on the pool.
        # So far it's not required since the builder
        # will be in single instance
        pass

        actual_reservations = self._get_pool_reservations(pool_uuid)

        # FIXME(akremenetsky): We use the simplest resource comparation,
        # there are CPU and RAM. It's ok right now but in the future
        # it should be a driver story to compare resources of a pool.
        pool = self._get_pool(pool_uuid)

        avail_cores = pool.all_cores - sum(
            r.cores for r in actual_reservations
        )
        avail_ram = pool.all_ram - sum(r.ram for r in actual_reservations)

        # The simplest case, try to acquire all reservations
        req_cores = sum(r.cores for r in reservations)
        req_ram = sum(r.ram for r in reservations)

        # All reservations are fit into the pool
        if avail_cores >= req_cores and avail_ram >= req_ram:
            for r in reservations:
                r.insert()
                LOG.info(
                    "The reservation %s(core=%s, ram=%s) has been created",
                    r.uuid,
                    r.cores,
                    r.ram,
                )
            return reservations

        # Not all reservations are fit into the pool
        # Try to acquire as much as possible
        machine_reservation_map = collections.defaultdict(list)
        for r in reservations:
            machine_reservation_map[r.machine].append(r)

        # Acquire reservations per machine
        acquired_reservations = []
        reschedule_machines = []
        for machine, machine_reservations in machine_reservation_map.items():
            req_cores = sum(r.cores for r in machine_reservations)
            req_ram = sum(r.ram for r in machine_reservations)

            # Check if there are enough resources for this machine
            if avail_cores >= req_cores and avail_ram >= req_ram:
                for r in machine_reservations:
                    r.insert()
                    LOG.info(
                        "The reservation %s(core=%s, ram=%s) has been created",
                        r.uuid,
                        r.cores,
                        r.ram,
                    )
                avail_cores -= req_cores
                avail_ram -= req_ram
                acquired_reservations += machine_reservations
            else:
                LOG.warning(
                    "Not enough resources to create the "
                    "reservation for the machine %s",
                    machine,
                )
                reschedule_machines.append(machine)

        # TODO(akremenetsky): Release the lock
        pass

        # Reschedule the machines
        self._reschedule_machines(reschedule_machines)

        return acquired_reservations

    def _iteration(self) -> None:
        with contexts.Context().session_manager():
            # Actualize the status of the builder
            self._actualize_status()

            # Get all machines associated with this builder
            machines = self._get_machines()

            if not machines:
                LOG.debug("No machine to build")
                return

            # Get all volumes associated with these machines
            volumes = self._get_volumes(machines)

            # Get all reservations associated with these machines
            reservations = self._get_reservations(machines)

            # Reserve resources for each machine.
            # Distribute the result by pools.
            new_reservations = collections.defaultdict(list)
            ready_machines = set()
            in_build_machines = {}
            for m in machines:
                new_machine_reservations = self._allocate_pool_reservations(
                    m, volumes.get(m, []), reservations.get(m, [])
                )

                # Need additional reservations for the machine
                if new_machine_reservations:
                    in_build_machines[m.uuid] = {
                        r.uuid for r in new_machine_reservations
                    }
                    new_reservations[m.pool].extend(new_machine_reservations)
                    continue

                # Mark the machine as ready to launch

                # FIXME(akremenetsky): Some additional resources may be
                # required in the future, for instance ports, GPUs, other
                # external devices.
                ready_machines.add(m.uuid)

            # Try to acquire allocated reservations
            acquired_reservations = set()
            for pool_uuid, pool_reservations in new_reservations.items():
                try:
                    _reservations = self._acquire_pool_reservations(
                        pool_uuid, pool_reservations
                    )
                except Exception:
                    LOG.exception(
                        "Error acquiring reservations for pool %s", pool_uuid
                    )
                # Accumulate acquired reservations
                acquired_reservations |= {r.uuid for r in _reservations}

            # Mark machines ready if all reservations are acquired
            for machine_uuid, need_reservations in in_build_machines.items():
                if not (need_reservations - acquired_reservations):
                    ready_machines.add(machine_uuid)

            for machine in machines:
                if machine.uuid in ready_machines:
                    try:
                        self._mark_machine_ready(machine)
                    except Exception:
                        LOG.exception(
                            "Error marking machine %s as ready", machine.uuid
                        )
