#    Copyright 2025-2026 Genesis Corporation.
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

import pytest
from bazooka import exceptions as bazooka_exc

from genesis_core.common import constants as common_c
from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam import constants as iam_c


class TestIdp(base.BaseIamResourceTest):
    IDP_ENDPOINT = "iam/idp"

    def _collection_url(self, client):
        return client.build_collection_uri([self.IDP_ENDPOINT])

    def _resource_url(self, client, uuid: str):
        return client.build_resource_uri([self.IDP_ENDPOINT, uuid])

    def _iam_client_uri(self, iam_client_uuid: str):
        return f"/v1/iam/clients/{iam_client_uuid}"

    def _build_create_payload(self, iam_client_uuid: str):
        return {
            "name": "test-idp",
            "description": "test-idp-desc",
            "callback_uri": "http://example.test/callback",
            "iam_client": self._iam_client_uri(iam_client_uuid),
        }

    def _create_idp(self, client, iam_client_uuid: str):
        url = self._collection_url(client)
        response = client.post(url, json=self._build_create_payload(iam_client_uuid))
        assert response.status_code == 201
        return response.json()

    def test_create_idp_unauthenticated_fails(self, user_api_noauth_client):
        client = user_api_noauth_client()
        url = self._collection_url(client)

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.post(
                url,
                json=self._build_create_payload(
                    iam_client_uuid=common_c.DEFAULT_CLIENT_UUID
                ),
            )

    def test_create_idp_no_permission_fails(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)
        url = self._collection_url(client)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.post(
                url,
                json=self._build_create_payload(
                    iam_client_uuid=auth_test1_user.client_uuid
                ),
            )

    def test_create_idp_with_permission_success(self, user_api_client, auth_test1_user):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
            ],
        )
        idp = self._create_idp(client, iam_client_uuid=auth_test1_user.client_uuid)

        assert idp["name"] == "test-idp"

    def test_list_idp_no_permission_fails(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)
        url = self._collection_url(client)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.get(url)

    def test_list_idp_with_permission_success(self, user_api_client, auth_user_admin):
        admin_client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
                iam_c.PERMISSION_IDP_READ_ALL,
            ],
        )
        self._create_idp(
            admin_client,
            iam_client_uuid=common_c.DEFAULT_CLIENT_UUID,
        )

        url = self._collection_url(admin_client)
        result = admin_client.get(url).json()

        assert isinstance(result, list)
        assert len(result) > 0

    def test_update_idp_no_permission_fails(
        self, user_api_client, auth_user_admin, auth_test1_user
    ):
        admin_client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
                iam_c.PERMISSION_IDP_UPDATE,
            ],
        )
        idp = self._create_idp(
            admin_client,
            iam_client_uuid=common_c.DEFAULT_CLIENT_UUID,
        )

        client = user_api_client(auth_test1_user)
        url = self._resource_url(client, idp["uuid"])

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.put(url, json={"name": "updated"})

    def test_update_idp_with_permission_success(self, user_api_client, auth_user_admin):
        admin_client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
                iam_c.PERMISSION_IDP_UPDATE,
            ],
        )
        idp = self._create_idp(
            admin_client,
            iam_client_uuid=common_c.DEFAULT_CLIENT_UUID,
        )

        url = self._resource_url(admin_client, idp["uuid"])
        response = admin_client.put(url, json={"name": "updated"})
        assert response.status_code == 200
        assert response.json()["name"] == "updated"

    def test_delete_idp_no_permission_fails(
        self, user_api_client, auth_user_admin, auth_test1_user
    ):
        admin_client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
                iam_c.PERMISSION_IDP_DELETE,
            ],
        )
        idp = self._create_idp(
            admin_client,
            iam_client_uuid=common_c.DEFAULT_CLIENT_UUID,
        )

        client = user_api_client(auth_test1_user)
        url = self._resource_url(client, idp["uuid"])

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.delete(url)

    def test_delete_idp_with_permission_success(self, user_api_client, auth_user_admin):
        admin_client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_IDP_CREATE,
                iam_c.PERMISSION_IDP_DELETE,
            ],
        )
        idp = self._create_idp(
            admin_client,
            iam_client_uuid=common_c.DEFAULT_CLIENT_UUID,
        )

        url = self._resource_url(admin_client, idp["uuid"])
        response = admin_client.delete(url)
        assert response.status_code == 204

        # Ensure it is gone
        with pytest.raises(bazooka_exc.NotFoundError):
            admin_client.get(url)
