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

import uuid as sys_uuid

from bazooka import exceptions as bazooka_exc
import pytest
from restalchemy.common import contexts

from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam.dm import models as iam_models


TEST_PROJECT_ID = str(sys_uuid.uuid4())


class TestClients(base.BaseIamResourceTest):
    SIGNATURE_ALGORITHM = {
        "kind": "HS256",
        "secret_uuid": "00000000-0000-0000-0000-000000000001",
        "previous_secret_uuid": None,
    }

    def test_create_iam_client_by_admin(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        iam_client_name = "test_client[admin-user]"

        iam_client = client.create_iam_client(
            name=iam_client_name,
            client_id="client_id",
            secret="12345678",
            signature_algorithm=self.SIGNATURE_ALGORITHM,
        )

        assert iam_client["name"] == iam_client_name

    def test_create_iam_client_by_user1(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        iam_client_name = "test_client[admin-user]"

        signature_algorithm = {
            "kind": "HS256",
            "secret_uuid": "00000000-0000-0000-0000-000000000001",
            "previous_secret_uuid": None,
        }

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.create_iam_client(
                name=iam_client_name,
                client_id="client_id",
                secret="12345678",
                signature_algorithm=signature_algorithm,
            )

    def test_list_iam_clients_by_admin(self, user_api_client, auth_user_admin):
        client = user_api_client(auth_user_admin)

        iam_clients = client.list_iam_clients()

        assert len(iam_clients) > 0

    def test_list_iam_clients_by_user(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.list_iam_clients()

    def test_get_iam_clients_by_admin(self, user_api_client, auth_user_admin):
        client = user_api_client(auth_user_admin)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"

        iam_client = client.get_iam_client(uuid=iam_client_uuid)

        assert iam_client["uuid"] == iam_client_uuid

    def test_get_iam_clients_by_user(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"

        iam_client = client.get_iam_client(uuid=iam_client_uuid)

        assert iam_client["uuid"] == iam_client_uuid

    def test_update_iam_clients_by_admin(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"
        new_name = "new_name"

        result = client.update_iam_client(
            uuid=iam_client_uuid,
            name=new_name,
        )

        assert result["name"] == new_name

    def test_update_iam_clients_rules_by_admin(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        iam_client = client.create_iam_client(
            name="test_client_rules",
            client_id=f"test_client_id_{sys_uuid.uuid4().hex[:8]}",
            secret="12345678",
            signature_algorithm=self.SIGNATURE_ALGORITHM,
        )

        rules = [{
            "kind": "admin_bypass",
            "bypass_users": []
        }]
        result = client.update_iam_client(
            uuid=iam_client["uuid"],
            rules=rules,
        )

        assert result["rules"] == rules

    def test_update_iam_clients_by_user(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"
        new_name = "new_name"

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.update_iam_client(
                uuid=iam_client_uuid,
                name=new_name,
            )

    def test_delete_iam_clients_by_admin(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"

        iam_client = client.delete_iam_client(uuid=iam_client_uuid)

        assert iam_client is None

    def test_delete_iam_clients_by_user(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        iam_client_uuid = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.delete_iam_client(uuid=iam_client_uuid)

    def test_me_wo_organization_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        result = client.me()

        assert result["user"]["uuid"] == auth_test1_user.uuid
        assert result["organization"] == []
        assert result["project_id"] is None

    def test_me_with_organization_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth_test1_user,
        )
        client.create_organization("OrganizationName1")
        client.create_organization("OrganizationName2")

        result = client.me()

        assert result["user"]["uuid"] == auth_test1_user.uuid
        assert len(result["organization"]) == 2
        assert result["project_id"] is None

    def test_me_with_organization_and_project_success(
        self, user_api_client, auth_test1_p1_user
    ):
        client = user_api_client(auth_test1_p1_user)

        result = client.me()

        assert result["user"]["uuid"] == auth_test1_p1_user.uuid
        assert len(result["organization"]) == 1
        assert result["project_id"] == auth_test1_p1_user.project_id

    def test_http_code_with_invalid_token(self, user_api_noauth_client):
        client = user_api_noauth_client()
        url = client.build_collection_uri(["iam/roles"])

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.get(url)

    def test_token_ttl_success(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["ttl"] = 1.0
        token_params["refresh_ttl"] = 2.0

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        assert token_info["refresh_expires_in"] == 1

    def test_logout_deletes_token_from_db(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        me = client.me()

        assert me["user"]["uuid"] == auth_test1_user.uuid

        logout_url = client.build_resource_uri(
            [
                "iam/clients",
                auth_test1_user.client_uuid,
                "actions",
                "logout",
                "invoke",
            ]
        )
        client.post(url=logout_url)

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.me()

    def test_get_token_with_invalid_client_id_error(
        self, user_api_noauth_client, auth_test1_user
    ):
        client = user_api_noauth_client()
        token_params = auth_test1_user.get_password_auth_params()
        token_params["client_id"] = "wrong-client-id"

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.post(
                url=auth_test1_user.get_token_url(endpoint=client.endpoint),
                data=token_params,
            )

    def test_get_token_with_invalid_client_secret_error(
        self, user_api_noauth_client, auth_test1_user
    ):
        client = user_api_noauth_client()
        token_params = auth_test1_user.get_password_auth_params()
        token_params["client_secret"] = "wrong-client-secret"

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.post(
                url=auth_test1_user.get_token_url(endpoint=client.endpoint),
                data=token_params,
            )

    def test_get_token_invalid_credentials_no_user_and_wrong_password_same_error(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        url = auth_test1_user.get_token_url(endpoint=client.endpoint)

        no_user_params = auth_test1_user.get_password_auth_params()
        no_user_params["username"] = "user_does_not_exist"
        no_user_params["password"] = "obviously-wrong-password"

        wrong_password_params = auth_test1_user.get_password_auth_params()
        wrong_password_params["password"] = "obviously-wrong-password"

        with pytest.raises(bazooka_exc.BadRequestError) as no_user_exc:
            client.post(url=url, data=no_user_params)
        with pytest.raises(bazooka_exc.BadRequestError) as wrong_password_exc:
            client.post(url=url, data=wrong_password_params)

        assert type(no_user_exc.value) is type(wrong_password_exc.value)
        assert not isinstance(no_user_exc.value, bazooka_exc.NotFoundError)
        assert not isinstance(
            wrong_password_exc.value, bazooka_exc.NotFoundError
        )

    @pytest.fixture(
        scope="function",
        params=[
            ("project",),
            ("project:default",),
            (f"project:{TEST_PROJECT_ID}",),
        ],
    )
    def scope_test(self, request):
        return request.param[0]

    def test_get_no_scoped_token_success(
        self, user_api_client, auth_test1_user, decode_id_token
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == ""
        assert id_token["project_id"] is None

    def test_get_empty_scoped_token_success(
        self, user_api_client, auth_test1_user, decode_id_token
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = ""

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == ""
        assert id_token["project_id"] is None

    def test_get_scoped_token_no_project_no_organization_success(
        self, user_api_client, auth_test1_user, decode_id_token, scope_test
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] is None

    def test_get_scoped_token_no_project_one_organization_success(
        self, user_api_client, auth_test1_user, decode_id_token, scope_test
    ):
        client = user_api_client(auth_test1_user)
        client.create_organization("OrganizationName1")
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] is None

    def test_get_scoped_token_one_project_one_organization_success(
        self, user_api_client, auth_test1_user, decode_id_token, scope_test
    ):
        client = user_api_client(auth_test1_user)
        org = client.create_organization("OrganizationName1")
        project = client.create_project(
            org["uuid"], "ProjectName1", uuid=TEST_PROJECT_ID
        )
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] == project["uuid"]

    def test_get_scoped_token_two_project_two_organization_success(
        self, user_api_client, auth_test1_user, decode_id_token, scope_test
    ):
        client = user_api_client(auth_test1_user)
        org1 = client.create_organization("OrganizationName1")
        project = client.create_project(
            org1["uuid"], "ProjectName1Org1", uuid=TEST_PROJECT_ID
        )
        client.create_project(org1["uuid"], "ProjectName2Org1")
        org2 = client.create_organization("OrganizationName2")
        client.create_project(org2["uuid"], "ProjectName1Org2")
        client.create_project(org2["uuid"], "ProjectName2Org2")
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = decode_id_token(token_info["id_token"])
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] == project["uuid"]

    def test_refresh_token_wo_scope_success(
        self, user_api_client, auth_test1_user, decode_id_token
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = "test"
        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        refreshed_token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_info["refresh_token"],
            },
        ).json()

        first_id_token = decode_id_token(token_info["id_token"])
        second_id_token = decode_id_token(refreshed_token_info["id_token"])
        assert token_info["scope"] == "test"
        assert first_id_token["project_id"] is None
        assert refreshed_token_info["scope"] == "test"
        assert second_id_token["project_id"] is None

    def test_refresh_to_scoped_token_one_project_one_organization_success(
        self, user_api_client, auth_test1_user, decode_id_token, scope_test
    ):
        client = user_api_client(auth_test1_user)
        org = client.create_organization("OrganizationName1")
        project = client.create_project(
            org["uuid"], "ProjectName1", uuid=TEST_PROJECT_ID
        )
        token_params = auth_test1_user.get_password_auth_params()
        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        refreshed_token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_info["refresh_token"],
                "scope": scope_test,
            },
        ).json()

        first_id_token = decode_id_token(token_info["id_token"])
        second_id_token = decode_id_token(refreshed_token_info["id_token"])
        assert token_info["scope"] == ""
        assert first_id_token["project_id"] is None
        assert refreshed_token_info["scope"] == scope_test
        assert second_id_token["project_id"] == project["uuid"]

    def test_garbage_refresh_token_with_scope_error(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.BadRequestError):
            client.post(
                url=auth_test1_user.get_token_url(endpoint=client.endpoint),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": "1234",  # garbage
                    "scope": "project:859aaa4f-9fcb-4433-8bc0-a84232a1177f",
                },
            )

    def test_invalid_grant_type_error(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.BadRequestError):
            client.post(
                url=auth_test1_user.get_token_url(endpoint=client.endpoint),
                data={"grant_type": "obviously invalid"},
            )
