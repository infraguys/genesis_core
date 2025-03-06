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
from urllib.parse import urljoin

import pytest
import requests

from genesis_core.node.dm import models
from genesis_core.tests.functional import utils as test_utils
from genesis_core.tests.functional import conftest
from genesis_core.orch_api.api import app as orch_app


class TestNodeOrchApi:
    @pytest.fixture(scope="class")
    def orch_api_service(self):
        class ApiRestService(test_utils.RestServiceTestCase):
            __FIRST_MIGRATION__ = conftest.FIRST_MIGRATION
            __LAST_MIGRATION__ = conftest.LAST_MIGRATION
            __APP__ = orch_app.get_api_application()

        rest_service = ApiRestService()
        rest_service.setup_class()

        yield rest_service

        rest_service.teardown_class()

    @pytest.fixture()
    def orch_api(self, orch_api_service: test_utils.RestServiceTestCase):
        orch_api_service.setup_method()

        yield orch_api_service

        orch_api_service.teardown_method()

    def test_netboots_default_net(
        self, orch_api: test_utils.RestServiceTestCase
    ):
        uuid = sys_uuid.uuid4()
        url = urljoin(orch_api.base_url, f"boots/{str(uuid)}")

        response = requests.get(url)

        assert response.status_code == 200
        assert response.text.startswith("#!ipxe")
        assert "initrd" in response.text
        assert "vmlinuz" in response.text
        assert "gc_base_url" in response.text

    def test_netboots_hd_boot(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        orch_api: test_utils.RestServiceTestCase,
    ):
        uuid = sys_uuid.uuid4()
        machine = machine_factory(
            boot="hd0",
            uuid=uuid,
            firmware_uuid=uuid,
            pool=sys_uuid.UUID(default_pool["uuid"]),
        )
        pool = models.MachinePool.restore_from_simple_view(**default_pool)
        pool.insert()

        machine = models.Machine.restore_from_simple_view(**machine)
        machine.insert()

        url = urljoin(orch_api.base_url, f"boots/{machine.uuid}")

        response = requests.get(url)

        assert response.status_code == 200
        assert response.text.startswith("#!ipxe")
        assert "initrd" not in response.text
        assert "vmlinuz" not in response.text
        assert "0x80" in response.text
