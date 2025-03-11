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

import os
import typing as tp
import uuid as sys_uuid

import pytest
from gcl_iam import algorithms
from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.common import constants as c
from genesis_core.common import utils
from genesis_core.node import constants as nc
from genesis_core.node.dm import models as node_models
from genesis_core.user_api.api import app as user_app
from genesis_core.tests.functional import utils as test_utils


FIRST_MIGRATION = "0000-root-d34de1.py"


@pytest.fixture(scope="session")
def hs256_algorithm():
    secret = os.getenv("HS256_KEY", c.DEFAULT_HS256_KEY)
    return algorithms.HS256(key=secret)


@pytest.fixture(scope="session")
def context_storage(
    hs256_algorithm: algorithms.AbstractAlgorithm,
):
    return utils.get_context_storage(
        global_salt=os.getenv("GLOBAL_SALT", c.DEFAULT_GLOBAL_SALT),
        token_algorithm=hs256_algorithm,
    )


@pytest.fixture(scope="session")
def admin_username():
    return c.DEFAULT_ADMIN_USERNAME


@pytest.fixture(scope="session")
def admin_password():
    return os.getenv("ADMIN_PASSWORD", c.DEFAULT_ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def default_client_id():
    return c.DEFAULT_CLIENT_ID


@pytest.fixture(scope="session")
def default_client_secret():
    return os.getenv("DEFAULT_CLIENT_SECRET", c.DEFAULT_CLIENT_SECRET)


@pytest.fixture(scope="session")
def default_client_uuid():
    return c.DEFAULT_CLIENT_UUID


@pytest.fixture(scope="module")
def user_api_service(hs256_algorithm, context_storage):
    class ApiRestService(test_utils.RestServiceTestCase):
        __FIRST_MIGRATION__ = FIRST_MIGRATION
        __APP__ = user_app.build_wsgi_application(
            context_storage=context_storage,
            token_algorithm=hs256_algorithm,
        )

    rest_service = ApiRestService()
    rest_service.setup_class()

    yield rest_service

    rest_service.teardown_class()


@pytest.fixture()
def user_api(user_api_service: test_utils.RestServiceTestCase):
    user_api_service.setup_method()

    yield user_api_service

    user_api_service.teardown_method()


@pytest.fixture()
def auth_user_admin(
    admin_username: str,
    admin_password: str,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    return iam_clients.GenesisCoreAuth(
        username=admin_username,
        password=admin_password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
    )


@pytest.fixture()
def auth_test1_user(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    password = "test1"
    client = user_api_client(auth_user_admin)
    result = client.create_user(username="test1", password=password)

    return iam_clients.GenesisCoreAuth(
        username=result["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=result["uuid"],
        email=result["email"],
    )


@pytest.fixture()
def user_api_client(user_api):

    def build_client(
        auth: iam_clients.GenesisCoreAuth,
        permissions: list[str] = None,
        project_id: str = None,
    ):
        permissions = permissions or []
        client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth,
        )

        client.set_permissions_to_user(
            user_uuid=auth.uuid,
            permissions=permissions,
            project_id=project_id,
        )

        return client

    return build_client


@pytest.fixture()
def user_api_noauth_client(user_api):
    return lambda: iam_clients.GenesisCoreTestNoAuthRESTClient(
        f"{user_api.get_endpoint()}v1/"
    )


@pytest.fixture
def machine_agent_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "agent",
        status: str = nc.MachineAgentStatus.ACTIVE.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        obj = node_models.MachineAgent(
            uuid=uuid,
            name=name,
            status=status,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def node_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "node",
        cores: int = 1,
        ram: int = 1024,
        image: str = "ubuntu_24.04",
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = nc.NodeStatus.NEW.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        node = node_models.Node(
            uuid=uuid,
            name=name,
            cores=cores,
            ram=ram,
            image=image,
            project_id=project_id,
            status=status,
            **kwargs,
        )
        view = node.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def pool_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        agent: sys_uuid.UUID | None = None,
        name: str = "pool-default",
        driver_spec: dict | None = None,
        status: str = nc.MachinePoolStatus.ACTIVE.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        driver_spec = driver_spec or {"driver": "libvirt"}
        pool = node_models.MachinePool(
            uuid=uuid,
            agent=agent,
            name=name,
            status=status,
            driver_spec=driver_spec,
            **kwargs,
        )
        view = pool.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def machine_factory(default_pool: tp.Dict[str, tp.Any]):
    def factory(
        uuid: sys_uuid.UUID | None = None,
        pool: sys_uuid.UUID | None = None,
        name: str = "node",
        cores: int = 1,
        ram: int = 1024,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = nc.MachineStatus.ACTIVE.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        pool = pool or sys_uuid.UUID(default_pool["uuid"])
        machine = node_models.Machine(
            uuid=uuid,
            pool=pool,
            name=name,
            cores=cores,
            ram=ram,
            project_id=project_id,
            status=status,
            **kwargs,
        )
        view = machine.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def default_machine_agent(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    machine_agent_factory: tp.Callable,
):
    uuid = sys_uuid.UUID("00000000-1110-0000-0000-000000000000")
    default_agent = machine_agent_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["machine_agents"])
    client.post(url, json=default_agent)

    yield default_agent

    url = client.build_resource_uri(["machine_agents", uuid])
    client.delete(url)


@pytest.fixture()
def default_pool(
    pool_factory: tp.Callable,
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
):
    uuid = sys_uuid.UUID("00000000-1111-0000-0000-000000000000")
    default_pool = pool_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["hypervisors"])
    client.post(url, json=default_pool)

    return default_pool


@pytest.fixture
def default_node(
    node_factory: tp.Callable,
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
):
    uuid = sys_uuid.UUID("00000000-1112-0000-0000-000000000000")
    default_node = node_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["nodes"])
    client.post(url, json=default_node)

    yield default_node

    url = client.build_resource_uri(["nodes", uuid])
    client.delete(url)
