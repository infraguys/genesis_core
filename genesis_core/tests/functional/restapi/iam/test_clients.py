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

from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam import constants as c


class TestClients(base.BaseIamResourceTest):

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
