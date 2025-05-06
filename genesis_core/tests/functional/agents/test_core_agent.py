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

import os
import json
import tempfile
import typing as tp
import uuid as sys_uuid
from unittest import mock

import pytest

from genesis_core.common import system
from genesis_core.agents.clients import orch
from genesis_core.agents.core import service as core_service
from genesis_core.agents.dm import models
from genesis_core.orch_api.dm import models as orch_models
from genesis_core.node.dm import models as node_models
from genesis_core.config.dm import models as config_models


MACHINE_UUID = sys_uuid.UUID("44b5857b-c15d-47f2-bed1-00fecd137208")


class DummyResp(tp.NamedTuple):
    data: dict

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


class DummyRestClient:
    def __init__(
        self,
        agent: models.CoreAgent,
        machine: models.Machine,
        node: models.Node,
        config: config_models.Config,
        render: config_models.Render,
    ) -> None:
        view = machine.dump_to_simple_view()
        machine = orch_models.Machine.restore_from_simple_view(**view)
        self._machine = machine
        self._core_agent = orch_models.CoreAgent(
            uuid=agent.uuid, machine=machine
        )
        self._node = node
        self._config = config
        self._render = render

    def _get(self, url: str, *args, **kwargs):
        pass

    def get(self, url: str, *args, **kwargs):
        if "actions" in url:
            return self.actions(url, *args, **kwargs)

        return self._get(url, *args, **kwargs)

    def put(self, url: str, *, json, **kwargs):
        if "renders" in url:
            # Render models of CP and DP are pretty different
            # so build a correct DP model almost by hand.
            o_render = orch_models.OrchRenderModel(
                uuid=self._render.uuid,
                config=self._render.config.uuid,
                node=self._node.uuid,
                status=self._render.status,
                content=self._render.content,
            )
            view = o_render.dump_to_simple_view()
            view.update(json)
            return DummyResp(data=view)

        if "machines" in url:
            view = self._machine.dump_to_simple_view()
            view.update(json)
            return DummyResp(data=view)

        raise ValueError(f"Undefined url: {url}")

    def post(self, url: str, json, **kwargs):
        if "interfaces" in url:
            return DummyResp(data=json)

        if "machines" in url:
            return DummyResp(data=self._machine.dump_to_simple_view())

        raise ValueError(f"Undefined url: {url}")

    def actions(self, url, *args, **kwargs):
        if "get_payload" in url:
            return DummyResp(data=self._core_agent.get_payload())

        raise ValueError(f"Unknown action: {url}")


@mock.patch.object(
    system,
    "system_uuid",
    lambda: MACHINE_UUID,
)
class TestCoreAgent:

    @pytest.fixture
    def payload_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield os.path.join(temp_dir, "payload.json")

    def test_agent(
        self,
        machine_factory: tp.Callable,
        node_factory: tp.Callable,
        config_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        payload_path: str,
    ):
        node_uuid = sys_uuid.uuid4()
        node = node_factory(uuid=node_uuid)
        node = models.Node.restore_from_simple_view(**node)
        node.insert()

        # NOTE(akremenetsky): It's a dirty hack for GitHub runners
        # since they don't allow to invoke `getlogin`.
        try:
            owner = os.getlogin()
            group = os.getlogin()
        except OSError:
            owner = group = "ubuntu"

        path = os.path.join(os.path.dirname(payload_path), "etc/test.conf")
        config = config_factory(
            target_node=node_uuid,
            path=path,
            owner=owner,
            group=group,
        )
        config = config_models.Config.restore_from_simple_view(**config)
        config.insert()
        render = config.render(node_uuid)
        render.status = "ACTIVE"
        render.insert()

        machine = machine_factory(
            uuid=MACHINE_UUID,
            boot="hd0",
            node=node_uuid,
            pool=sys_uuid.UUID(default_pool["uuid"]),
        )

        machine = models.Machine.restore_from_simple_view(**machine)
        machine.insert()

        agent = models.CoreAgent(uuid=machine.uuid, machine=machine.uuid)
        agent.insert()

        client = DummyRestClient(agent, machine, node, config, render)
        orch_api = orch.OrchAPI(
            "http://127.0.0.1",
            http_client=client,
        )

        service = core_service.CoreAgentService(
            orch_api=orch_api,
            payload_path=payload_path,
        )

        service._iteration()

        assert os.path.exists(payload_path)

        with open(payload_path, "r") as f:
            payload = json.load(f)

        assert payload["node"]["uuid"] == str(node.uuid)
        assert payload["machine"]["uuid"] == str(machine.uuid)

        assert os.path.exists(path)

        with open(path, "r") as f:
            assert "test" in f.read()
