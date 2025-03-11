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

from bazooka import exceptions as bazooka_exc
import pytest

from genesis_core.user_api.iam import constants as c


class TestUsers:

    USERS_ENDPOINT = "iam/users"

    def test_create_user_success(self, user_api_noauth_client):
        client = user_api_noauth_client()
        url = client.build_collection_uri([self.USERS_ENDPOINT])

        result = client.post(
            url,
            json={
                "username": "test",
                "password": "test",
                "description": "Test User",
                "first_name": "Test",
                "last_name": "Testovich",
                "email": "test@example.com",
            },
        )

        body = result.json()
        assert result.status_code == 201
        assert body["password"] == "*******"

    def test_list_users_wo_auth_bad_request(self, user_api_noauth_client):
        client = user_api_noauth_client()
        url = client.build_collection_uri([self.USERS_ENDPOINT])

        with pytest.raises(bazooka_exc.BadRequestError):
            client.get(url)

    def test_list_users_admin_auth_success(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri([self.USERS_ENDPOINT])

        result = client.get(url)

        body = result.json()
        assert result.status_code == 200
        assert len(body) == 1

    def test_list_users_test1_auth_forbidden(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        url = client.build_collection_uri([self.USERS_ENDPOINT])

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.get(url)

    def test_list_users_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth=auth_test1_user,
            permissions=[
                c.PERMISSION_USER_LISTING,
            ],
        )
        url = client.build_collection_uri([self.USERS_ENDPOINT])

        result = client.get(url)

        assert result.status_code == 200

    def test_get_other_user_test1_auth_success(
        self, user_api_client, auth_test1_user, auth_user_admin
    ):
        client = user_api_client(auth_test1_user)
        url = client.build_resource_uri(
            [self.USERS_ENDPOINT, auth_user_admin.uuid]
        )

        result = client.get(url)

        assert result.status_code == 200


class TestOrganizations:

    ORGS_ENDPOINT = "iam/organizations"
    ORGS_BINDINGS_ENDPOINT = "iam/organization_members"

    def test_create_organization_wo_auth_bad_request(
        self, user_api_noauth_client
    ):
        client = user_api_noauth_client()
        url = client.build_collection_uri([self.ORGS_ENDPOINT])

        with pytest.raises(bazooka_exc.BadRequestError):
            client.post(
                url,
                json={
                    "name": "Test Organization",
                    "description": "Test Organization Description",
                },
            )
