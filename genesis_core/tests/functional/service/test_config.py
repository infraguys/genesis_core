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

import datetime
import typing as tp
import uuid as sys_uuid

from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.config import service
from genesis_core.config.dm import models
from genesis_core.node.dm import models as node_models


class TestConfigService:

    def setup_method(self) -> None:
        # Run service
        self._service = service.ConfigService()

    def teardown_method(self) -> None:
        pass

    def test_no_configs(
        self,
        default_node: tp.Dict[str, tp.Any],
    ):
        self._service._iteration()

    def test_new_config(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"])
        )

        url = client.build_collection_uri(["config/configs"])
        response = client.post(url, json=config)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()

        renders = models.Render.objects.get_all()
        configs = models.Config.objects.get_all()

        assert len(renders) == 1
        assert len(configs) == 1
        render = renders[0]
        config = configs[0]

        assert config.status == "IN_PROGRESS"
        assert render.status == "NEW"
        assert render.config == config
        assert str(render.node) == default_node["uuid"]

    def test_new_config_fake_node(
        self,
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(target_node=sys_uuid.uuid4())

        url = client.build_collection_uri(["config/configs"])
        response = client.post(url, json=config)
        output = response.json()

        assert output["status"] == "NEW"

        self._service._iteration()

        renders = models.Render.objects.get_all()
        configs = models.Config.objects.get_all()

        assert len(renders) == 0
        assert len(configs) == 0

    def test_new_config_render_text(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        render = models.Render.objects.get_one()

        assert render.content == "TEST"

    def test_in_progress_configs(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "IN_PROGRESS"

        render = models.Render.objects.get_one()
        render.status = "ACTIVE"
        render.update()

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "ACTIVE"

    def test_in_progress_configs_no_renders(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "IN_PROGRESS"

        render = models.Render.objects.get_one()
        render.delete()

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "IN_PROGRESS"

    def test_orphan_configs(
        self,
        node_factory: tp.Callable,
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)
        default_node = node_factory()

        url = client.build_collection_uri(["nodes"])
        client.post(url, json=default_node)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        config = models.Config.objects.get_one()
        renders = models.Render.objects.get_all()
        assert config.status == "IN_PROGRESS"
        assert len(renders) == 1

        node_models.Node.objects.get_all()[0].delete()

        self._service._iteration_number = 0
        self._service._handle_orphan_configs(datetime.timedelta(seconds=-1))

        configs = models.Config.objects.get_all()
        renders = models.Render.objects.get_all()
        assert len(configs) == 0
        assert len(renders) == 0

    def test_orphan_configs_no(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        config = models.Config.objects.get_one()
        renders = models.Render.objects.get_all()
        assert config.status == "IN_PROGRESS"
        assert len(renders) == 1

        self._service._iteration_number = 0
        self._service._handle_orphan_configs(datetime.timedelta(seconds=-1))

        configs = models.Config.objects.get_all()
        renders = models.Render.objects.get_all()
        assert len(configs) == 1
        assert len(renders) == 1

    def test_update_configs(
        self,
        default_node: tp.Dict[str, tp.Any],
        config_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        config = config_factory(
            target_node=sys_uuid.UUID(default_node["uuid"]),
            content_body="TEST",
        )

        url = client.build_collection_uri(["config/configs"])
        client.post(url, json=config)

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "IN_PROGRESS"

        render = models.Render.objects.get_one()
        render.status = "ACTIVE"
        render.update()

        self._service._iteration()

        config = models.Config.objects.get_one()
        assert config.status == "ACTIVE"

        update = {"owner": "test"}
        url = client.build_resource_uri(["config/configs", str(config.uuid)])
        response = client.put(url, json=update)
        assert response.status_code == 200

        output = response.json()
        assert output["owner"] == "test"

        self._service._iteration()

        config = models.Config.objects.get_one()
        renders = models.Render.objects.get_all()

        assert config.status == "IN_PROGRESS"
        assert len(renders) == 1
