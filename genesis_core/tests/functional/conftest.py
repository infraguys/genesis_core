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

import typing as tp
import uuid as sys_uuid
from urllib.parse import urljoin

import pytest
import requests

from genesis_core.common import constants as c
from genesis_core.node import constants as nc
from genesis_core.node.dm import models as node_models
from genesis_core.user_api.api import app as user_app

from genesis_core.tests.functional import utils as test_utils


FIRST_MIGRATION = "0000-init-compute-tables-0234eb"
LAST_MIGRATION = "0002-add-volumes-tables-a6972c"


@pytest.fixture(scope="module")
def user_api_service():
    class ApiRestService(test_utils.RestServiceTestCase):
        __FIRST_MIGRATION__ = FIRST_MIGRATION
        __LAST_MIGRATION__ = LAST_MIGRATION
        __APP__ = user_app.get_api_application()

    rest_service = ApiRestService()
    rest_service.setup_class()

    yield rest_service

    rest_service.teardown_class()


@pytest.fixture()
def user_api(user_api_service: test_utils.RestServiceTestCase):
    user_api_service.setup_method()

    yield user_api_service

    user_api_service.teardown_method()


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
    user_api: test_utils.RestServiceTestCase,
    machine_agent_factory: tp.Callable,
):
    uuid = sys_uuid.UUID("00000000-1110-0000-0000-000000000000")
    default_agent = machine_agent_factory(uuid=uuid)
    url = urljoin(user_api.base_url, "machine_agents/")
    requests.post(url, json=default_agent)

    yield default_agent

    requests.delete(urljoin(user_api.base_url, f"machine_agents/{uuid}"))


@pytest.fixture
def default_pool(
    user_api: test_utils.RestServiceTestCase, pool_factory: tp.Callable
):
    uuid = sys_uuid.UUID("00000000-1111-0000-0000-000000000000")
    default_pool = pool_factory(uuid=uuid)
    url = urljoin(user_api.base_url, "hypervisors/")
    requests.post(url, json=default_pool)

    yield default_pool

    requests.delete(urljoin(user_api.base_url, f"hypervisors/{uuid}"))


@pytest.fixture
def default_node(
    user_api: test_utils.RestServiceTestCase, node_factory: tp.Callable
):
    uuid = sys_uuid.UUID("00000000-1112-0000-0000-000000000000")
    default_node = node_factory(uuid=uuid)
    url = urljoin(user_api.base_url, "nodes/")
    requests.post(url, json=default_node)

    yield default_node

    requests.delete(urljoin(user_api.base_url, f"nodes/{uuid}"))
