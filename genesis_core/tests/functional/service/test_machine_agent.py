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
from unittest import mock

import pytest
import netaddr
from gcl_iam.tests.functional import clients as iam_clients
from restalchemy.dm import filters as dm_filters

from genesis_core.compute.machine.pool.driver import base as driver_base
from genesis_core.compute.machine import service
from genesis_core.compute.dm import models
from genesis_core.common import constants as c
from genesis_core.compute import constants as nc


def fake_load_driver(
    *args: tp.Any, **kwargs: tp.Any
) -> driver_base.AbstractPoolDriver:
    return TestMachineAgentService.pool_driver


@mock.patch.object(
    models.MachinePool,
    "load_driver",
    fake_load_driver,
)
class TestMachineAgentService:
    pool_driver = None

    def setup_method(self) -> None:
        # Run service
        self._service = service.MachineAgentService(
            agent_uuid=sys_uuid.uuid4()
        )
        self.__class__.pool_driver = mock.MagicMock()

    def teardown_method(self) -> None:
        self.__class__.pool_driver = None

    def _save_pool_driver(self, driver: driver_base.AbstractPoolDriver):
        self.__class__.pool_driver = driver

    def _get_pool_driver(self) -> driver_base.AbstractPoolDriver:
        return self.__class__.pool_driver

    def _schedule_pool(
        self, pool_uuid: str, agent_uuid: str
    ) -> models.MachinePool:
        pool = models.MachinePool.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(pool_uuid),
            },
        )
        pool.agent = sys_uuid.UUID(agent_uuid)
        pool.update()
        return pool

    def _schedule_machine(
        self,
        machine_uuid: str,
        pool: str | models.MachinePool,
        subnet: models.Subnet | None = None,
    ) -> models.Machine:
        # Node
        node_uuid = sys_uuid.uuid4()
        node = models.Node(
            uuid=node_uuid,
            name="foo-node",
            cores=1,
            ram=1024,
            image="ubuntu_24.04",
            project_id=c.SERVICE_PROJECT_ID,
        )
        node.insert()

        # Port
        if subnet is not None:
            port = models.Port(
                uuid=sys_uuid.uuid4(),
                node=node_uuid,
                subnet=subnet.uuid,
                project_id=subnet.project_id,
                ipv4=netaddr.IPAddress("10.0.0.1"),
                netmask=netaddr.IPAddress("255.255.255.0"),
                status=nc.PortStatus.ACTIVE.value,
            )
            port.insert()

        # Machine
        machine = models.Machine.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(machine_uuid),
            },
        )
        if isinstance(pool, str):
            pool = models.MachinePool.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(pool),
                },
            )
        machine.pool = pool.uuid
        machine.node = node_uuid
        machine.update()

        # Volume
        volume_name = "root-volume"
        volume_uuid = sys_uuid.uuid5(node_uuid, volume_name)
        volume = models.Volume(
            uuid=volume_uuid,
            name=volume_name,
            size=nc.DEF_ROOT_DISK_SIZE,
            node=node_uuid,
            project_id=c.SERVICE_PROJECT_ID,
        )
        volume.insert()

        return machine, node

    def _schedule_node(
        self, node_uuid: str, machine: str | models.Machine
    ) -> models.Node:
        node = models.Node.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(node_uuid),
            },
        )
        if isinstance(machine, str):
            machine = models.Machine.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(machine),
                },
            )
        machine.node = sys_uuid.UUID(node_uuid)
        machine.update()
        return node

    @pytest.mark.usefixtures("user_api_client", "auth_user_admin")
    def test_empty_iteration(self):
        self._service._iteration()

    def test_create_machine_no_driver(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )

        # Create machine
        machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(uuid=machine_uuid)
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        self._schedule_machine(str(machine_uuid), pool)

        # Default pool dosn't have any driver, so no actual creation
        # should happen
        self._service._iteration()

    def test_create_machine_net_not_ready(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(uuid=foo_machine_uuid)
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, _ = self._schedule_machine(str(foo_machine_uuid), pool)

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            create_machine_called = False
            delete_machine_called = False

            def __init__(self):
                pass

            def create_machine(
                self,
                machine: models.Machine,
                volumes: tp.Iterable,
                ports: tp.Iterable,
            ) -> None:
                self.create_machine_called = True

            def delete_machine(self, machine: models.Machine) -> None:
                self.delete_machine_called = True

        self._save_pool_driver(FakePoolDriver())

        # Perform iteration
        self._service._iteration()

        assert not self.pool_driver.create_machine_called
        assert not self.pool_driver.delete_machine_called

    def test_create_machine(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        default_subnet: models.Subnet,
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(uuid=foo_machine_uuid)
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, _ = self._schedule_machine(
            str(foo_machine_uuid),
            pool,
            default_subnet,
        )

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            create_machine_called = False
            delete_machine_called = False
            created_machines = []

            def __init__(self):
                pass

            def create_machine(
                self,
                machine: models.Machine,
                volumes: tp.Iterable,
                ports: tp.Iterable,
            ) -> None:
                self.create_machine_called = True
                self.created_machines.append(machine)

                # Defautl volume
                assert len(volumes) == 1

            def delete_machine(self, machine: models.Machine) -> None:
                self.delete_machine_called = True

        self._save_pool_driver(FakePoolDriver())

        # Perform iteration
        self._service._iteration()

        assert self.pool_driver.create_machine_called
        assert not self.pool_driver.delete_machine_called
        assert {m.uuid for m in self.pool_driver.created_machines} == {
            machine_foo.uuid,
        }

    def test_create_several_machines(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
        default_subnet: models.Subnet,
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(uuid=foo_machine_uuid)
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        bar_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(uuid=bar_machine_uuid)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, _ = self._schedule_machine(
            str(foo_machine_uuid), pool, default_subnet
        )
        machine_bar, _ = self._schedule_machine(
            str(bar_machine_uuid), pool, default_subnet
        )

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            create_machine_called = False
            delete_machine_called = False
            created_machines = []

            def __init__(self):
                pass

            def create_machine(
                self,
                machine: models.Machine,
                volumes: tp.Iterable,
                ports: tp.Iterable,
            ) -> None:
                self.create_machine_called = True
                self.created_machines.append(machine)

            def delete_machine(self, machine: models.Machine) -> None:
                self.delete_machine_called = True

        self._save_pool_driver(FakePoolDriver())

        # Perform iteration
        self._service._iteration()

        assert self.pool_driver.create_machine_called
        assert not self.pool_driver.delete_machine_called
        assert {m.uuid for m in self.pool_driver.created_machines} == {
            machine_foo.uuid,
            machine_bar.uuid,
        }

    def test_delete_machine(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Prepare fake pool driver
        machine_uuid = sys_uuid.uuid4()

        class FakePoolDriver(driver_base.DummyPoolDriver):
            delete_machine_called = False
            deleted_machines = []

            def __init__(self):
                pass

            def list_machines(self) -> tp.List[models.Machine]:
                machine_spec = machine_factory(uuid=machine_uuid)
                m = models.Machine.restore_from_simple_view(**machine_spec)
                return [m]

            def delete_machine(
                self, machine: models.Machine, delete_volumes: bool = True
            ) -> None:
                self.delete_machine_called = True
                self.deleted_machines.append(machine)

        self._save_pool_driver(FakePoolDriver())

        # Perform iteration
        self._service._iteration()

        assert self.pool_driver.delete_machine_called
        assert {m.uuid for m in self.pool_driver.deleted_machines} == {
            machine_uuid
        }

    def test_create_machine_in_build(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(
            uuid=foo_machine_uuid,
            build_status=nc.MachineBuildStatus.IN_BUILD.value,
        )
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, _ = self._schedule_machine(str(foo_machine_uuid), pool)

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            create_machine_called = False
            delete_machine_called = False

            def __init__(self):
                pass

            def create_machine(
                self, machine: models.Machine, volumes: tp.Iterable
            ) -> None:
                self.create_machine_called = True

            def delete_machine(self, machine: models.Machine) -> None:
                self.delete_machine_called = True

        self._save_pool_driver(FakePoolDriver())

        # Perform iteration
        self._service._iteration()

        assert not self.pool_driver.create_machine_called
        assert not self.pool_driver.delete_machine_called

    def test_actualize_pool(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()
        cores = pool.all_cores
        ram = pool.all_ram

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(
            uuid=foo_machine_uuid,
            cores=2,
            ram=2048,
        )
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, _ = self._schedule_machine(str(foo_machine_uuid), pool)

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            def __init__(self):
                pass

            def list_machines(self) -> tp.List[models.Machine]:
                return [machine_foo]

            def create_machine(
                self, machine: models.Machine, volumes: tp.Iterable
            ) -> None:
                pass

            def delete_machine(self, machine: models.Machine) -> None:
                pass

        self._save_pool_driver(FakePoolDriver())

        # Perform iterations
        self._service._iteration()

        url = client.build_resource_uri(["hypervisors", str(pool.uuid)])
        response = client.get(url)
        output = response.json()

        assert response.status_code == 200
        assert output["avail_cores"] == cores - 2
        assert output["avail_ram"] == ram - 2048

    def test_update_machine_set_cores_ram(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(
            uuid=foo_machine_uuid,
        )
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, node_foo = self._schedule_machine(
            str(foo_machine_uuid), pool
        )

        node_foo.cores = 2
        node_foo.ram = 4096
        node_foo.update()

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            set_machine_cores_called: bool = False
            set_machine_ram_called: bool = False

            def __init__(self):
                pass

            def list_machines(self) -> tp.List[models.Machine]:
                return [machine_foo]

            def set_machine_cores(
                self, machine: models.Machine, cores: int
            ) -> None:
                self.set_machine_cores_called = True
                assert cores == 2

            def set_machine_ram(
                self, machine: models.Machine, ram: int
            ) -> None:
                self.set_machine_ram_called = True
                assert ram == 4096

        self._save_pool_driver(FakePoolDriver())

        # Perform iterations
        self._service._iteration()

        assert self.pool_driver.set_machine_cores_called
        assert self.pool_driver.set_machine_ram_called

    def test_update_machine_image(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        machine_factory: tp.Callable,
        default_node: tp.Dict[str, tp.Any],
        default_pool: tp.Dict[str, tp.Any],
        default_machine_agent: tp.Dict[str, tp.Any],
    ):
        self._service._agent_uuid = sys_uuid.UUID(
            default_machine_agent["uuid"]
        )

        # Schedule pool to the default machine agent
        pool = self._schedule_pool(
            default_pool["uuid"], default_machine_agent["uuid"]
        )
        pool.driver_spec = {"driver": "dummy"}
        pool.update()

        # Create machines
        foo_machine_uuid = sys_uuid.uuid4()
        machine_spec = machine_factory(
            uuid=foo_machine_uuid,
            boot="hd0",
        )
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["machines"])
        client.post(url, json=machine_spec)

        # Schedule machine to the pool
        machine_foo, node_foo = self._schedule_machine(
            str(foo_machine_uuid), pool
        )

        node_foo.image = "my-net-foo-image"
        node_foo.update()

        # Prepare fake pool driver
        class FakePoolDriver(driver_base.DummyPoolDriver):
            reset_machine_called: bool = False

            def __init__(self):
                pass

            def list_machines(self) -> tp.List[models.Machine]:
                return [machine_foo]

            def reset_machine(self, machine: models.Machine) -> None:
                assert machine.image is None
                self.reset_machine_called = True

        self._save_pool_driver(FakePoolDriver())

        # Perform iterations
        self._service._iteration()

        assert self.pool_driver.reset_machine_called
