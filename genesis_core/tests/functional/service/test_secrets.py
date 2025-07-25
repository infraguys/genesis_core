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

from restalchemy.storage.sql import engines
from gcl_iam.tests.functional import clients as iam_clients
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.secret import service
from genesis_core.secret.dm import models


class TestSecretsServiceBuilder:

    def setup_method(self) -> None:
        # Run service
        self._service = service.SecretServiceBuilder()

    def teardown_method(self) -> None:
        pass

    def test_no_secrets(
        self,
        default_node: tp.Dict[str, tp.Any],
    ):
        self._service._iteration()

    def test_new_password(
        self,
        default_node: tp.Dict[str, tp.Any],
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        password = password_factory(
            # target_node=sys_uuid.UUID(default_node["uuid"])
        )

        url = client.build_collection_uri(["secret/passwords"])
        response = client.post(url, json=password)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        passwords = models.Password.objects.get_all()

        assert len(target_resources) == 1
        assert len(passwords) == 1
        password = passwords[0]

        assert password.status == "IN_PROGRESS"

    def test_in_progress_passwords(
        self,
        default_node: tp.Dict[str, tp.Any],
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        password = password_factory()

        url = client.build_collection_uri(["secret/passwords"])
        client.post(url, json=password)

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["value"]["status"] = "ACTIVE"
        view["value"]["value"] = "mynewpassword"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "ACTIVE"
        assert password.value == "mynewpassword"

    def test_update_passwords(
        self,
        default_node: tp.Dict[str, tp.Any],
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        password = password_factory()

        url = client.build_collection_uri(["secret/passwords"])
        client.post(url, json=password)

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["value"]["status"] = "ACTIVE"
        view["value"]["value"] = "mynewpassword"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "ACTIVE"

        update = {"name": "test"}
        url = client.build_resource_uri(
            ["secret/passwords", str(password.uuid)]
        )
        response = client.put(url, json=update)
        assert response.status_code == 200

        output = response.json()
        assert output["name"] == "test"

        password = models.Password.objects.get_one()
        assert password.status == "NEW"

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

    def test_delete_passwords(
        self,
        default_node: tp.Dict[str, tp.Any],
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        password = password_factory()

        url = client.build_collection_uri(["secret/passwords"])
        client.post(url, json=password)

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

        password.delete()

        self._service._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        assert len(target_resources) == 0

    def test_update_passwords_active_on_valid_hash(
        self,
        default_node: tp.Dict[str, tp.Any],
        password_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        password = password_factory()

        url = client.build_collection_uri(["secret/passwords"])
        client.post(url, json=password)

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["hash"] = "222"
        view["value"]["status"] = "ACTIVE"
        view["value"]["value"] = "mynewpassword"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        password = models.Password.objects.get_one()
        assert password.status == "IN_PROGRESS"

        render_actual_resource.full_hash = "3333"
        render_actual_resource.hash = target_resources[0].hash
        render_actual_resource.update()

        self._service._iteration()

        cert = models.Password.objects.get_one()
        assert cert.status == "ACTIVE"

    def test_new_certificate(
        self,
        default_node: tp.Dict[str, tp.Any],
        cert_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        cert = cert_factory()

        url = client.build_collection_uri(["secret/certificates"])
        response = client.post(url, json=cert)
        output = response.json()

        assert response.status_code == 201
        assert output["status"] == "NEW"

        self._service._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        certificates = models.Certificate.objects.get_all()

        assert len(target_resources) == 1
        assert len(certificates) == 1
        certiface = certificates[0]

        assert cert["uuid"] == str(certiface.uuid)
        assert certiface.status == "IN_PROGRESS"

    def test_in_progress_certificates(
        self,
        default_node: tp.Dict[str, tp.Any],
        cert_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        cert = cert_factory()

        url = client.build_collection_uri(["secret/certificates"])
        client.post(url, json=cert)

        self._service._iteration()

        certificate = models.Certificate.objects.get_one()
        assert certificate.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["value"]["status"] = "ACTIVE"
        view["value"]["key"] = "mykey"
        view["value"]["cert"] = "mycert"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        certificate = models.Certificate.objects.get_one()
        assert certificate.status == "ACTIVE"
        assert certificate.key == "mykey"
        assert certificate.cert == "mycert"

    def test_update_certificates(
        self,
        default_node: tp.Dict[str, tp.Any],
        cert_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        cert = cert_factory()

        url = client.build_collection_uri(["secret/certificates"])
        client.post(url, json=cert)

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["value"]["status"] = "ACTIVE"
        view["value"]["key"] = "mykey"
        view["value"]["cert"] = "mycert"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "ACTIVE"

        update = {"name": "test"}
        url = client.build_resource_uri(
            ["secret/certificates", str(cert.uuid)]
        )
        response = client.put(url, json=update)
        assert response.status_code == 200

        output = response.json()
        assert output["name"] == "test"

        cert = models.Certificate.objects.get_one()
        assert cert.status == "NEW"

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "IN_PROGRESS"

    def test_delete_certificates(
        self,
        default_node: tp.Dict[str, tp.Any],
        cert_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        cert = cert_factory()

        url = client.build_collection_uri(["secret/certificates"])
        client.post(url, json=cert)

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "IN_PROGRESS"

        cert.delete()

        self._service._iteration()

        target_resources = ua_models.TargetResource.objects.get_all()
        assert len(target_resources) == 0

    def test_update_certificates_active_on_valid_hash(
        self,
        default_node: tp.Dict[str, tp.Any],
        cert_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        agent = ua_models.UniversalAgent(
            uuid=sys_uuid.UUID(default_node["uuid"]),
            node=sys_uuid.UUID(default_node["uuid"]),
            name="UniversalAgent",
        )
        agent.insert()

        client = user_api_client(auth_user_admin)

        cert = cert_factory()

        url = client.build_collection_uri(["secret/certificates"])
        client.post(url, json=cert)

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "IN_PROGRESS"

        target_resources = ua_models.TargetResource.objects.get_all()
        view = target_resources[0].dump_to_simple_view()
        view.pop("master", None)
        view.pop("agent", None)
        view.pop("tracked_at", None)
        view["status"] = "ACTIVE"
        view["full_hash"] = "1111"
        view["hash"] = "2222"
        view["value"]["status"] = "ACTIVE"
        view["value"]["key"] = "mykey"
        view["value"]["cert"] = "mycert"
        render_actual_resource = ua_models.Resource.restore_from_simple_view(
            **view
        )
        render_actual_resource.insert()

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "IN_PROGRESS"

        render_actual_resource.full_hash = "3333"
        render_actual_resource.hash = target_resources[0].hash
        render_actual_resource.update()

        self._service._iteration()

        cert = models.Certificate.objects.get_one()
        assert cert.status == "ACTIVE"
