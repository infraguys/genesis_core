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

from genesis_core.node.scheduler import service
from genesis_core.node.dm import models


class TestSchedulerService:

    def setup_method(self) -> None:
        # Run service
        self._service = service.NodeSchedulerService()

    def teardown_method(self) -> None:
        pass

    def test_nothing_scheduler(self, default_pool: tp.Dict[str, tp.Any]):
        self._service._iteration()

    def test_schedule_pool(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._iteration()
        pool = models.MachinePool.objects.get_all()

        assert len(pool) == 1
        assert str(pool[0].uuid) == default_pool["uuid"]
        assert str(pool[0].agent) == default_machine_agent["uuid"]

        unsheduled = self._service._get_unscheduled_pools()
        assert len(unsheduled) == 0

    def test_schedule_node(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_node: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
    ):
        view = builder_factory()
        builder = models.Builder.restore_from_simple_view(**view)
        builder.insert()

        self._service._iteration()
        machines = models.Machine.objects.get_all()
        volumes = models.MachineVolume.objects.get_all()

        assert len(machines) == 1
        assert len(volumes) == 1
        assert str(machines[0].node) == default_node["uuid"]
        assert str(volumes[0].node) == default_node["uuid"]
        assert volumes[0].machine == machines[0].uuid

    def test_schedule_node_no_builders(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_node: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._iteration()
        machines = models.Machine.objects.get_all()
        volumes = models.MachineVolume.objects.get_all()

        assert len(machines) == 0
        assert len(volumes) == 0

    def test_schedule_unscheduled_machine(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_node: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        machine_factory: tp.Callable,
    ):
        view = builder_factory()
        builder = models.Builder.restore_from_simple_view(**view)
        builder.insert()

        view = machine_factory(pool=None)
        machine = models.Machine.restore_from_simple_view(**view)
        machine.insert()

        self._service._iteration()
        machines = models.Machine.objects.get_all()

        assert len(machines) == 2
        assert str(machines[0].pool) == default_pool["uuid"]
        assert str(machines[1].pool) == default_pool["uuid"]
