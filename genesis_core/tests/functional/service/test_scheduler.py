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
import collections
import uuid as sys_uuid

from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.compute.scheduler import service
from genesis_core.compute.dm import models
from genesis_core.compute.scheduler.driver.filters import available
from genesis_core.compute.scheduler.driver.weighter import relative


class TestSchedulerService:

    def setup_method(self) -> None:
        # Run service
        pool_filters = [
            available.CoresRamAvailableFilter(),
        ]
        pool_weighters = [
            relative.RelativeCoreRamWeighter(),
        ]
        machine_filters = [
            available.HWCoresRamAvailableFilter(),
        ]
        machine_weighters = [
            relative.SimpleMachineWeighter(),
        ]
        self._service = service.SchedulerService(
            pool_filters=pool_filters,
            pool_weighters=pool_weighters,
            machine_filters=machine_filters,
            machine_weighters=machine_weighters,
        )

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

    def test_schedule_two_pools_single_iteration(
        self,
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        pool_factory: tp.Callable,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        view = builder_factory()
        builder = models.Builder.restore_from_simple_view(**view)
        builder.insert()

        uuid_foo = sys_uuid.uuid4()
        foo_pool = pool_factory(uuid=uuid_foo)
        url = client.build_collection_uri(["hypervisors"])
        client.post(url, json=foo_pool)

        uuid_bar = sys_uuid.uuid4()
        bar_pool = pool_factory(uuid=uuid_bar)
        url = client.build_collection_uri(["hypervisors"])
        client.post(url, json=bar_pool)

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        pools = models.MachinePool.objects.get_all()

        assert len(pools) == 2
        assert len(machines) == 4
        assert set(m.pool for m in machines) == {uuid_foo, uuid_bar}
        assert collections.Counter(
            str(m.pool) for m in machines
        ) == collections.Counter(**{f"{uuid_foo}": 2, f"{uuid_bar}": 2})

    def test_schedule_two_pools_different_iterations(
        self,
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        pool_factory: tp.Callable,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        view = builder_factory()
        builder = models.Builder.restore_from_simple_view(**view)
        builder.insert()

        uuid_foo = sys_uuid.uuid4()
        foo_pool = pool_factory(uuid=uuid_foo)
        url = client.build_collection_uri(["hypervisors"])
        client.post(url, json=foo_pool)

        uuid_bar = sys_uuid.uuid4()
        bar_pool = pool_factory(uuid=uuid_bar)
        url = client.build_collection_uri(["hypervisors"])
        client.post(url, json=bar_pool)

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        pools = models.MachinePool.objects.get_all()

        assert len(pools) == 2
        assert len(machines) == 2
        assert set(m.pool for m in machines) == {uuid_foo, uuid_bar}
        assert collections.Counter(
            str(m.pool) for m in machines
        ) == collections.Counter(**{f"{uuid_foo}": 1, f"{uuid_bar}": 1})

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = node_factory()
        node = models.Node.restore_from_simple_view(**view)
        node.insert()

        view = builder_factory()
        builder = models.Builder.restore_from_simple_view(**view)
        builder.insert()

        self._service._iteration()

        machines = models.Machine.objects.get_all()
        pools = models.MachinePool.objects.get_all()

        assert len(pools) == 2
        assert len(machines) == 4
        assert set(m.pool for m in machines) == {uuid_foo, uuid_bar}
        assert collections.Counter(
            str(m.pool) for m in machines
        ) == collections.Counter(**{f"{uuid_foo}": 2, f"{uuid_bar}": 2})

    def test_schedule_hw_node(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        machine_factory: tp.Callable,
        pool_factory: tp.Callable,
        node_factory: tp.Callable,
    ):
        builder = builder_factory()
        builder = models.Builder.restore_from_simple_view(**builder)
        builder.insert()

        # HW machine pool
        hw_pool = pool_factory(machine_type="HW")
        hw_pool = models.MachinePool.restore_from_simple_view(**hw_pool)
        hw_pool.insert()

        # HW machine
        hw_machine = machine_factory(
            machine_type="HW",
            pool=hw_pool.uuid,
            status="IDLE",
            cores=2,
            ram=4096,
        )
        hw_machine = models.Machine.restore_from_simple_view(**hw_machine)
        hw_machine.insert()

        # HW node
        node = node_factory(node_type="HW")
        node = models.Node.restore_from_simple_view(**node)
        node.insert()

        self._service._iteration()
        machines = models.Machine.objects.get_all()
        nodes = models.Node.objects.get_all()

        assert len(machines) == 1
        assert len(nodes) == 1
        assert machines[0].node == node.uuid
        assert machines[0].status == "SCHEDULED"
        assert nodes[0].status == "SCHEDULED"

    def test_schedule_hw_node_filtered_out_all(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        machine_factory: tp.Callable,
        pool_factory: tp.Callable,
        node_factory: tp.Callable,
    ):
        builder = builder_factory()
        builder = models.Builder.restore_from_simple_view(**builder)
        builder.insert()

        # HW machine pool
        hw_pool = pool_factory(machine_type="HW")
        hw_pool = models.MachinePool.restore_from_simple_view(**hw_pool)
        hw_pool.insert()

        # HW machine
        hw_machine = machine_factory(
            machine_type="HW",
            pool=hw_pool.uuid,
            status="IDLE",
            cores=2,
            ram=512,
        )
        hw_machine = models.Machine.restore_from_simple_view(**hw_machine)
        hw_machine.insert()

        # HW node
        node = node_factory(node_type="HW", ram=1024)
        node = models.Node.restore_from_simple_view(**node)
        node.insert()

        self._service._iteration()
        machines = models.Machine.objects.get_all()
        nodes = models.Node.objects.get_all()

        assert len(machines) == 1
        assert len(nodes) == 1
        assert machines[0].node is None
        assert machines[0].status == "IDLE"
        assert nodes[0].status == "ERROR"
        assert nodes[0].description == "No suitable HW machines found"

    def test_schedule_hw_node_simple_weighter(
        self,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        builder_factory: tp.Callable,
        machine_factory: tp.Callable,
        pool_factory: tp.Callable,
        node_factory: tp.Callable,
    ):
        builder = builder_factory()
        builder = models.Builder.restore_from_simple_view(**builder)
        builder.insert()

        # HW machine pool
        hw_pool = pool_factory(machine_type="HW")
        hw_pool = models.MachinePool.restore_from_simple_view(**hw_pool)
        hw_pool.insert()

        # HW machines
        hw_machine = machine_factory(
            machine_type="HW",
            pool=hw_pool.uuid,
            status="IDLE",
            cores=4,
            ram=2048,
        )
        hw_machine = models.Machine.restore_from_simple_view(**hw_machine)
        hw_machine.insert()

        hw_machine = machine_factory(
            machine_type="HW",
            pool=hw_pool.uuid,
            status="IDLE",
            cores=6,
            ram=4096,
        )
        hw_machine = models.Machine.restore_from_simple_view(**hw_machine)
        hw_machine.insert()

        hw_machine = machine_factory(
            machine_type="HW",
            pool=hw_pool.uuid,
            status="IDLE",
            cores=1,
            ram=2048,
        )
        hw_machine = models.Machine.restore_from_simple_view(**hw_machine)
        hw_machine.insert()

        # HW node
        node = node_factory(node_type="HW", cores=1, ram=1024)
        node = models.Node.restore_from_simple_view(**node)
        node.insert()

        self._service._iteration()
        machines = models.Machine.objects.get_all()
        nodes = models.Node.objects.get_all()

        assert len(machines) == 3
        assert len(nodes) == 1

        for machine in machines:
            if machine.uuid == hw_machine.uuid:
                break
        else:
            raise AssertionError("Machine not found")

        assert machine.node == node.uuid
        assert machine.cores == 1
        assert machine.ram == 2048
        assert machine.status == "SCHEDULED"
        assert nodes[0].status == "SCHEDULED"
