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
import tempfile
import typing as tp
import uuid as sys_uuid
from unittest import mock

from restalchemy.dm import filters as dm_filters
from gcl_iam.tests.functional import clients as iam_clients
from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.agents.universal import utils as ua_utils
from gcl_sdk.agents.universal.clients.orch import db as orch_db
from gcl_sdk.agents.universal.clients.backend import db as db_back
from gcl_sdk.agents.universal.services import agent as ua_agent_service
from gcl_sdk.agents.universal.services import scheduler as ua_scheduler_service
from gcl_sdk.agents.universal.drivers import core as ua_core_drivers
from genesis_core.compute.dm import models as compute_models
from genesis_core.compute import constants as nc

from genesis_core.compute.node_set.builders import service
from genesis_core.compute.node_set.dm import models as node_set_models


def fake_system_uuid(*args, **kwargs):
    return sys_uuid.UUID("11111111-1111-1111-1111-111111111111")


@mock.patch.object(
    ua_utils,
    "system_uuid",
    fake_system_uuid,
)
class TestNodeSetBuilder:

    def setup_method(self) -> None:
        # Run service
        self._service = service.NodeSetBuilder(
            instance_model=node_set_models.NodeSet,
            project_id=nc.NODE_SET_PROJECT,
        )

        # Infra agent
        orch_client = orch_db.DatabaseOrchClient()
        agent_uuid = sys_uuid.uuid4()

        _, tmp_fs_path = tempfile.mkstemp(prefix="tf_", suffix=".json")
        self._tmp_fs_path = tmp_fs_path
        os.remove(self._tmp_fs_path)

        spec = db_back.ModelSpec(
            kind="set_agent_node",
            model=compute_models.Node,
            filters={"project_id": dm_filters.EQ(str(nc.NODE_SET_PROJECT))},
        )
        db_core_driver = ua_core_drivers.DatabaseCapabilityDriver(
            model_specs=[spec],
            target_fields_storage_path=self._tmp_fs_path,
        )

        caps_drivers = [
            db_core_driver,
        ]

        self._infra_agent = ua_agent_service.UniversalAgentService(
            agent_uuid=agent_uuid,
            orch_client=orch_client,
            caps_drivers=caps_drivers,
            facts_drivers=[],
            payload_path=None,
        )

        # Infra scheduler
        self._infra_scheduler = (
            ua_scheduler_service.UniversalAgentSchedulerService(
                capabilities=["set_agent_node"]
            )
        )

    def teardown_method(self) -> None:
        if os.path.exists(self._tmp_fs_path):
            os.remove(self._tmp_fs_path)

    def test_no_node_sets(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        default_node: tp.Dict[str, tp.Any],
    ):
        self._service._iteration()

    def test_new_node_set(
        self,
        node_set_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        # For agent to be available
        self._infra_agent._iteration()

        client = user_api_client(auth_user_admin)

        node_set = node_set_factory()
        node_set.pop("status", None)
        node_set.pop("nodes", None)

        url = client.build_collection_uri(["compute", "sets"])
        response = client.post(url, json=node_set)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 2
        assert {r.kind for r in target_resources} == {
            "set_agent_node",
            "node_set",
        }
        assert len(node_sets) == 1
        assert node_sets[0].status == "IN_PROGRESS"
        assert len(nodes) == 1

    def test_update_node_sets_replicas(
        self,
        node_set_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        # For agent to be available
        self._infra_agent._iteration()

        client = user_api_client(auth_user_admin)

        node_set = node_set_factory()
        node_set.pop("status", None)
        node_set.pop("nodes", None)

        url = client.build_collection_uri(["compute", "sets"])
        response = client.post(url, json=node_set)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        update = {
            "replicas": 2,
        }
        url = client.build_resource_uri(["compute", "sets", node_set["uuid"]])
        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 3
        assert {r.kind for r in target_resources} == {
            "set_agent_node",
            "node_set",
        }
        assert len(node_sets) == 1
        assert node_sets[0].status == "NEW"
        assert len(nodes) == 2

    def test_update_node_sets_replicas_shrink(
        self,
        node_set_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        # For agent to be available
        self._infra_agent._iteration()

        client = user_api_client(auth_user_admin)

        node_set = node_set_factory(replicas=2)
        node_set.pop("status", None)
        node_set.pop("nodes", None)

        url = client.build_collection_uri(["compute", "sets"])
        response = client.post(url, json=node_set)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        nodes = compute_models.Node.objects.get_all()
        assert len(nodes) == 2

        update = {
            "replicas": 1,
        }
        url = client.build_resource_uri(["compute", "sets", node_set["uuid"]])
        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 2
        assert {r.kind for r in target_resources} == {
            "set_agent_node",
            "node_set",
        }
        assert len(node_sets) == 1
        assert node_sets[0].status == "NEW"
        assert len(nodes) == 1
        assert len(node_sets[0].nodes) == 1

    def test_update_node_sets_cores(
        self,
        node_set_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        # For agent to be available
        self._infra_agent._iteration()

        client = user_api_client(auth_user_admin)

        node_set = node_set_factory()
        node_set.pop("status", None)
        node_set.pop("nodes", None)

        url = client.build_collection_uri(["compute", "sets"])
        response = client.post(url, json=node_set)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        update = {
            "cores": 2,
        }
        url = client.build_resource_uri(["compute", "sets", node_set["uuid"]])
        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 2
        assert {r.kind for r in target_resources} == {
            "set_agent_node",
            "node_set",
        }
        assert len(node_sets) == 1
        assert len(nodes) == 1
        assert nodes[0]["cores"] == 2

    def test_delete_node_set(
        self,
        node_set_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        # For agent to be available
        self._infra_agent._iteration()

        client = user_api_client(auth_user_admin)

        node_set = node_set_factory()
        node_set.pop("status", None)
        node_set.pop("nodes", None)

        url = client.build_collection_uri(["compute", "sets"])
        response = client.post(url, json=node_set)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 2
        assert {r.kind for r in target_resources} == {
            "set_agent_node",
            "node_set",
        }
        assert len(node_sets) == 1
        assert node_sets[0].status == "IN_PROGRESS"
        assert len(nodes) == 1

        url = client.build_resource_uri(["compute", "sets", node_set["uuid"]])
        response = client.delete(url)

        assert response.status_code == 204

        self._service._iteration()
        self._infra_scheduler._iteration()
        self._infra_agent._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        node_sets = node_set_models.NodeSet.objects.get_all()
        nodes = compute_models.Node.objects.get_all()

        assert len(target_resources) == 0
        assert len(node_sets) == 0
        assert len(nodes) == 0
