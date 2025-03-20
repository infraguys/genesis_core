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
import netaddr
import requests
from oslo_config import cfg

from genesis_core.node.dm import models
from genesis_core.common import constants as c
from genesis_core.tests.functional import utils as test_utils
from genesis_core.tests.functional import conftest
from genesis_core.orch_api.api import app as orch_app
from genesis_core.cmd import orch_api as orch_api_cmd


CONF = cfg.CONF


class TestNodeOrchApi:
    @pytest.fixture(scope="class")
    def orch_api_service(self):
        class ApiRestService(test_utils.RestServiceTestCase):
            __FIRST_MIGRATION__ = conftest.FIRST_MIGRATION
            __APP__ = orch_app.build_wsgi_application()

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
        CONF[orch_api_cmd.DOMAIN].gc_host = "10.20.0.2"

        uuid = sys_uuid.uuid4()
        url = urljoin(orch_api.base_url, f"boots/{str(uuid)}")

        response = requests.get(url)

        assert response.status_code == 200
        assert response.text.startswith("#!ipxe")
        assert "initrd" in response.text
        assert "vmlinuz" in response.text
        assert "gc_base_url" in response.text
        assert "tftp://10.20.0.2" in response.text

    def test_netboots_hd_boot(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        orch_api: test_utils.RestServiceTestCase,
    ):
        CONF[orch_api_cmd.DOMAIN].gc_host = "10.20.0.2"

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

    def test_netboots_default_net_custom_kernel_initrd(
        self, orch_api: test_utils.RestServiceTestCase
    ):
        CONF[orch_api_cmd.DOMAIN].kernel = "https://kernel.org/vmlinuz"
        CONF[orch_api_cmd.DOMAIN].initrd = "https://kernel.org/initrd.img"

        uuid = sys_uuid.uuid4()
        url = urljoin(orch_api.base_url, f"boots/{str(uuid)}")

        response = requests.get(url)

        assert response.status_code == 200
        assert response.text.startswith("#!ipxe")
        assert "initrd" in response.text
        assert "vmlinuz" in response.text
        assert "gc_base_url" in response.text
        assert "tftp://" not in response.text
        assert "https://kernel.org/vmlinuz" in response.text
        assert "https://kernel.org/initrd.img" in response.text

    def test_simple_core_agent(
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

        agent = models.CoreAgent(uuid=machine.uuid)
        agent.insert()

        url = urljoin(orch_api.base_url, f"core_agents/{agent.uuid}")

        response = requests.get(url)
        output = response.json()

        assert response.status_code == 200
        assert output["uuid"] == str(agent.uuid)
        assert (
            output["payload_updated_at"][:10]
            == str(agent.payload_updated_at)[:10]
        )

    def test_core_agent_get_payload(
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

        agent = models.CoreAgent(uuid=machine.uuid, machine=machine.uuid)
        agent.insert()

        url = urljoin(
            orch_api.base_url, f"core_agents/{agent.uuid}/actions/get_payload"
        )
        data = {
            "payload_updated_at": agent.payload_updated_at.isoformat(),
        }

        response = requests.get(url, json=data)
        output = response.json()

        assert response.status_code == 200
        assert output["payload_hash"]
        assert "machine" in output
        assert (
            output["payload_updated_at"]
            != agent.payload_updated_at.isoformat()
        )

    def test_core_agent_payload_already_actual(
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

        agent = models.CoreAgent(uuid=machine.uuid, machine=machine.uuid)
        agent.insert()

        url = urljoin(
            orch_api.base_url, f"core_agents/{agent.uuid}/actions/get_payload"
        )
        data = {
            "payload_updated_at": agent.payload_updated_at.isoformat(),
        }

        response = requests.get(url, json=data)
        output = response.json()

        assert response.status_code == 200
        assert "machine" in output
        assert (
            output["payload_updated_at"]
            != agent.payload_updated_at.isoformat()
        )

        # The second call should return the same state
        payload_updated_at = output["payload_updated_at"]
        payload_hash = output["payload_hash"]
        data = {
            "payload_updated_at": payload_updated_at,
            "payload_hash": payload_hash,
        }

        response = requests.get(url, json=data)
        output = response.json()

        assert response.status_code == 200
        assert output["payload_updated_at"] == payload_updated_at
        assert output["payload_hash"] == payload_hash
        assert "machine" not in output

    def test_core_agent_register_payload(
        self,
        machine_factory: tp.Callable,
        pool_factory: tp.Callable,
        orch_api: test_utils.RestServiceTestCase,
    ):
        uuid = sys_uuid.uuid4()
        machine = machine_factory(
            uuid=uuid,
            firmware_uuid=uuid,
            machine_type="HW",
        )
        machine["pool"] = None

        # HW machine pool
        hw_pool = pool_factory(
            machine_type="HW",
            driver_spec={},
        )
        hw_pool = models.MachinePool.restore_from_simple_view(**hw_pool)
        hw_pool.insert()

        agent = models.CoreAgent(uuid=uuid)
        agent.insert()

        url = urljoin(
            orch_api.base_url,
            f"core_agents/{agent.uuid}/actions/register_payload/invoke",
        )

        data = {
            "machine": machine,
            "node": None,
            "interfaces": [
                {
                    "name": "eth0",
                    "mac": "00:1A:2B:3C:4D:5E",
                    "ipv4": "10.0.0.1",
                    "mask": "255.255.255.0",
                    "mtu": 1500,
                }
            ],
        }

        response = requests.post(url, json=data)

        assert response.status_code == 200

        agent = models.CoreAgent.objects.get_one()
        machine = models.Machine.objects.get_one()
        # port = models.Port.objects.get_one()
        nodes = models.Node.objects.get_all()
        interface = models.Interface.objects.get_one()

        assert agent.machine == machine.uuid
        assert interface.ipv4 == netaddr.IPAddress("10.0.0.1")
        assert interface.mask == netaddr.IPAddress("255.255.255.0")
        assert interface.mac == "00:1A:2B:3C:4D:5E"
        assert interface.machine == machine.uuid
        assert len(nodes) == 0

    def test_machine_interfaces(
        self,
        machine_factory: tp.Callable,
        pool_factory: tp.Callable,
        orch_api: test_utils.RestServiceTestCase,
    ):
        uuid = sys_uuid.uuid4()
        machine = machine_factory(
            uuid=uuid,
            firmware_uuid=uuid,
            machine_type="HW",
        )
        machine["pool"] = None

        # HW machine pool
        hw_pool = pool_factory(
            machine_type="HW",
            driver_spec={},
        )
        hw_pool = models.MachinePool.restore_from_simple_view(**hw_pool)
        hw_pool.insert()

        agent = models.CoreAgent(uuid=uuid)
        agent.insert()

        url = urljoin(
            orch_api.base_url,
            f"core_agents/{agent.uuid}/actions/register_payload/invoke",
        )

        data = {
            "machine": machine,
            "node": None,
            "interfaces": [
                {
                    "name": "eth0",
                    "mac": "00:1A:2B:3C:4D:5E",
                    "ipv4": "10.0.0.1",
                    "mask": "255.255.255.0",
                    "mtu": 1500,
                }
            ],
        }

        response = requests.post(url, json=data)
        assert response.status_code == 200

        interface = models.Interface.objects.get_one()
        assert interface.mac == "00:1A:2B:3C:4D:5E"
        assert str(interface.ipv4) == "10.0.0.1"
        assert str(interface.mask) == "255.255.255.0"
        assert interface.mtu == 1500

    def test_core_agent_register_payload_vm(
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

        agent = models.CoreAgent(uuid=machine.uuid, machine=machine.uuid)
        agent.insert()

        url = urljoin(
            orch_api.base_url,
            f"core_agents/{agent.uuid}/actions/register_payload/invoke",
        )

        data = {
            "machine": machine.dump_to_simple_view(),
            "node": None,
            "interfaces": [
                {
                    "name": "eth0",
                    "mac": "00:1A:2B:3C:4D:5E",
                    "ipv4": "10.0.0.1",
                    "mask": "255.255.255.0",
                    "mtu": 1500,
                }
            ],
        }

        response = requests.post(url, json=data)
        assert response.status_code == 200

        machine = models.Machine.objects.get_one()
        assert machine.machine_type == "VM"
