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
import uuid as sys_uuid

from genesis_core.compute.builder import service
from genesis_core.compute.dm import models
from genesis_core.compute import constants as nc


class TestBuilderService:

    def setup_method(self) -> None:
        # Run service
        self._service = service.NodeBuilderService(
            service_uuid=sys_uuid.uuid4()
        )

    def teardown_method(self) -> None:
        pass

    def test_nothing_build(self, default_pool: tp.Dict[str, tp.Any]):
        builders = models.Builder.objects.get_all()
        assert len(builders) == 0

        self._service._iteration()

        builders = models.Builder.objects.get_all()
        assert len(builders) == 1

    def test_build(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        machine_factory: tp.Callable,
    ):
        self._service._actualize_status()

        # Schedule machine
        view = machine_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            build_status=nc.MachineBuildStatus.IN_BUILD.value,
            builder=self._service._service_uuid,
        )
        machine = models.Machine.restore_from_simple_view(**view)
        machine.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        reservations = models.MachinePoolReservations.objects.get_all()

        assert len(machines) == 1
        assert len(reservations) == 1

        machine: models.Machine = machines[0]
        reservation: models.MachinePoolReservations = reservations[0]

        assert machine.build_status == nc.MachineBuildStatus.READY
        assert machine.builder is None
        assert str(machine.pool) == default_pool["uuid"]
        assert machine.pool == reservation.pool
        assert reservation.cores == machine.cores
        assert reservation.ram == machine.ram

    def test_build_have_reservations(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        machine_factory: tp.Callable,
        machine_pool_reservation_factory: tp.Callable,
    ):
        self._service._actualize_status()

        # Schedule machine
        view = machine_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            build_status=nc.MachineBuildStatus.IN_BUILD.value,
            builder=self._service._service_uuid,
        )
        machine = models.Machine.restore_from_simple_view(**view)
        machine.insert()

        # Add reservations
        view = machine_pool_reservation_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            machine=machine.uuid,
            cores=machine.cores,
            ram=machine.ram,
        )
        reservation = models.MachinePoolReservations.restore_from_simple_view(
            **view
        )
        reservation.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        reservations = models.MachinePoolReservations.objects.get_all()

        assert len(machines) == 1
        assert len(reservations) == 1

        machine: models.Machine = machines[0]
        _reservation: models.MachinePoolReservations = reservations[0]

        assert machine.build_status == nc.MachineBuildStatus.READY
        assert machine.builder is None
        assert reservation.uuid == _reservation.uuid
        assert reservation.cores == _reservation.cores
        assert reservation.ram == _reservation.ram

    def test_build_already_ready(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        machine_factory: tp.Callable,
        machine_pool_reservation_factory: tp.Callable,
    ):
        self._service._actualize_status()

        # Schedule machine
        view = machine_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            build_status=nc.MachineBuildStatus.READY.value,
            builder=self._service._service_uuid,
        )
        machine = models.Machine.restore_from_simple_view(**view)
        machine.insert()

        # Add reservations
        view = machine_pool_reservation_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            machine=machine.uuid,
            cores=machine.cores,
            ram=machine.ram,
        )
        reservation = models.MachinePoolReservations.restore_from_simple_view(
            **view
        )
        reservation.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        reservations = models.MachinePoolReservations.objects.get_all()

        assert len(machines) == 1
        assert len(reservations) == 1

        machine: models.Machine = machines[0]
        _reservation: models.MachinePoolReservations = reservations[0]

        assert machine.build_status == nc.MachineBuildStatus.READY
        assert machine.builder is None
        assert reservation.uuid == _reservation.uuid
        assert reservation.cores == _reservation.cores
        assert reservation.ram == _reservation.ram

    def test_build_not_enough_resources(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        machine_factory: tp.Callable,
    ):
        self._service._actualize_status()

        # Schedule machine
        view = machine_factory(
            pool=sys_uuid.UUID(default_pool["uuid"]),
            build_status=nc.MachineBuildStatus.IN_BUILD.value,
            builder=self._service._service_uuid,
            cores=10,
        )
        machine = models.Machine.restore_from_simple_view(**view)
        machine.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        reservations = models.MachinePoolReservations.objects.get_all()

        assert len(machines) == 1
        assert len(reservations) == 0

        machine: models.Machine = machines[0]

        assert machine.build_status == nc.MachineBuildStatus.IN_BUILD
        assert machine.builder is None
        assert machine.pool is None
