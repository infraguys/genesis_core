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

from genesis_core.tests.functional.restapi.iam import base


TEST_PROJECT_ID = str(sys_uuid.uuid4())


class TestClients(base.BaseIamResourceTest):

    def test_create_iam_client_by_admin(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        iam_client_name = "test_client[admin-user]"

        iam_client = client.create_iam_client(
            name=iam_client_name,
            client_id="client_id",
            secret="12345678",
            redirect_url="http://127.0.0.1/",
        )

        assert iam_client["name"] == iam_client_name

    def test_create_iam_client_by_user1(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        iam_client_name = "test_client[admin-user]"

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.create_iam_client(
                name=iam_client_name,
                client_id="client_id",
                secret="12345678",
                redirect_url="http://127.0.0.1/",
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
            redirect_url="http://127.0.0.1/",
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
        self, user_api_client, auth_test1_user, hs256_algorithm
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == ""
        assert id_token["project_id"] is None

    def test_get_empty_scoped_token_success(
        self, user_api_client, auth_test1_user, hs256_algorithm
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = ""

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == ""
        assert id_token["project_id"] is None

    def test_get_scoped_token_no_project_no_organization_success(
        self, user_api_client, auth_test1_user, hs256_algorithm, scope_test
    ):
        client = user_api_client(auth_test1_user)
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] is None

    def test_get_scoped_token_no_project_one_organization_success(
        self, user_api_client, auth_test1_user, hs256_algorithm, scope_test
    ):
        client = user_api_client(auth_test1_user)
        client.create_organization("OrganizationName1")
        token_params = auth_test1_user.get_password_auth_params()
        token_params["scope"] = scope_test

        token_info = client.post(
            url=auth_test1_user.get_token_url(endpoint=client.endpoint),
            data=token_params,
        ).json()

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] is None

    def test_get_scoped_token_one_project_one_organization_success(
        self, user_api_client, auth_test1_user, hs256_algorithm, scope_test
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

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] == project["uuid"]

    def test_get_scoped_token_two_project_two_organization_success(
        self, user_api_client, auth_test1_user, hs256_algorithm, scope_test
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

        id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == scope_test
        assert id_token["project_id"] == project["uuid"]

    def test_refresh_token_wo_scope_success(
        self, user_api_client, auth_test1_user, hs256_algorithm
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

        first_id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        second_id_token = hs256_algorithm.decode(
            refreshed_token_info["id_token"], ignore_audience=True
        )
        assert token_info["scope"] == "test"
        assert first_id_token["project_id"] is None
        assert refreshed_token_info["scope"] == "test"
        assert second_id_token["project_id"] is None

    def test_refresh_to_scoped_token_one_project_one_organization_success(
        self, user_api_client, auth_test1_user, hs256_algorithm, scope_test
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

        first_id_token = hs256_algorithm.decode(
            token_info["id_token"], ignore_audience=True
        )
        second_id_token = hs256_algorithm.decode(
            refreshed_token_info["id_token"], ignore_audience=True
        )
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
