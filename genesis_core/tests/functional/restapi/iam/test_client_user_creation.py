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
from unittest import mock
from urllib.parse import urljoin

import pytest
import requests
from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam.dm import models as iam_models


class TestClientUserCreation(base.BaseIamResourceTest):

    def _create_iam_client_with_rules(
        self, client, name_suffix, rules
    ):
        """Factory method to create IamClient with rules."""
        iam_client = client.create_iam_client(
            name=f"test_client_{name_suffix}",
            client_id=f"test_client_id_{sys_uuid.uuid4().hex[:8]}",
            secret="12345678",
            redirect_url="http://127.0.0.1/",
        )
        if rules:
            client.update_iam_client(
                uuid=iam_client["uuid"],
                rules=rules
            )
        return iam_client["uuid"]

    @pytest.fixture
    def iam_client_with_admin_bypass_rule(
        self, user_api_client, auth_user_admin
    ):
        """Create IamClient with admin_bypass rule."""
        client = user_api_client(auth_user_admin)
        rules = [{"kind": "admin_bypass", "bypass_users": []}]
        return self._create_iam_client_with_rules(
            client, "admin_bypass", rules
        )

    @pytest.fixture
    def iam_client_with_admin_bypass_rule_with_email(
        self, user_api_client, auth_user_admin, auth_test1_user
    ):
        """Create IamClient with admin_bypass rule containing email."""
        client = user_api_client(auth_user_admin)
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        rules = [{"kind": "admin_bypass", "bypass_users": [user.email]}]
        return self._create_iam_client_with_rules(
            client, "admin_bypass_email", rules
        )

    @pytest.fixture
    def iam_client_with_admin_bypass_rule_with_uuid(
        self, user_api_client, auth_user_admin, auth_test1_user
    ):
        """Create IamClient with admin_bypass rule containing UUID."""
        client = user_api_client(auth_user_admin)
        rules = [{"kind": "admin_bypass", "bypass_users": [str(auth_test1_user.uuid)]}]
        return self._create_iam_client_with_rules(
            client, "admin_bypass_uuid", rules
        )

    @pytest.fixture
    def iam_client_with_admin_bypass_rule_restricted(
        self, user_api_client, auth_user_admin, auth_test1_user
    ):
        """Create IamClient with admin_bypass rule with specific user only."""
        client = user_api_client(auth_user_admin)
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        rules = [{"kind": "admin_bypass", "bypass_users": [user.email]}]
        return self._create_iam_client_with_rules(
            client, "admin_bypass_restricted", rules
        )

    @pytest.fixture
    def iam_client_with_firebase_app_check_rule(
        self, user_api_client, auth_user_admin
    ):
        """Create IamClient with firebase_app_check rule."""
        client = user_api_client(auth_user_admin)
        rules = [{
            "kind": "firebase_app_check",
            "credentials_path": "/tmp/fake-firebase-credentials.json",
            "allowed_app_ids": ["test-app-id"],
            "mode": "enforce"
        }]
        return self._create_iam_client_with_rules(
            client, "firebase_app_check", rules
        )

    def _get_access_token(self, user_api, auth):
        """Get access token from auth object."""
        client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth,
        )
        # Client automatically authenticates on init, token is cached
        assert "access_token" in client._auth_cache
        return client._auth_cache["access_token"]

    def _create_user_via_action(
        self, user_api, iam_client_uuid, username, password, email=None, headers=None
    ):
        """Create user via action endpoint."""
        url = urljoin(
            user_api.base_url,
            f"iam/clients/{iam_client_uuid}/actions/create_user/invoke"
        )
        data = {"username": username, "password": password}
        if email:
            data["email"] = email
        response = requests.post(
            url,
            json=data,
            headers=headers or {},
        )
        return response

    def test_create_user_admin_bypass_role_success(
        self, user_api, auth_user_admin,
        iam_client_with_admin_bypass_rule
    ):
        token = self._get_access_token(user_api, auth_user_admin)
        headers = {"Authorization": f"Bearer {token}"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_admin_bypass_rule,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 200
        user_data = response.json()
        assert "name" in user_data or "username" in user_data
        assert "uuid" in user_data

    def test_create_user_admin_bypass_email_success(
        self, user_api, auth_test1_user,
        iam_client_with_admin_bypass_rule_with_email
    ):
        token = self._get_access_token(user_api, auth_test1_user)
        headers = {"Authorization": f"Bearer {token}"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_admin_bypass_rule_with_email,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 200
        user_data = response.json()
        assert "name" in user_data or "username" in user_data
        assert "uuid" in user_data

    def test_create_user_admin_bypass_uuid_success(
        self, user_api, auth_test1_user,
        iam_client_with_admin_bypass_rule_with_uuid
    ):
        token = self._get_access_token(user_api, auth_test1_user)
        headers = {"Authorization": f"Bearer {token}"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_admin_bypass_rule_with_uuid,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 200
        user_data = response.json()
        assert "name" in user_data or "username" in user_data
        assert "uuid" in user_data

    def test_create_user_admin_bypass_invalid_token_forbidden(
        self, user_api, iam_client_with_admin_bypass_rule
    ):
        headers = {"Authorization": "Bearer invalid_token_12345"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_admin_bypass_rule,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 403
        error_data = response.json()
        assert "CanNotCreateUser" in error_data.get("type", "")

    def test_create_user_admin_bypass_user_not_in_list_forbidden(
        self, user_api, auth_test2_user,
        iam_client_with_admin_bypass_rule_restricted
    ):
        token = self._get_access_token(user_api, auth_test2_user)
        headers = {"Authorization": f"Bearer {token}"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_admin_bypass_rule_restricted,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 403
        error_data = response.json()
        assert "CanNotCreateUser" in error_data.get("type", "")
        assert "not allowed to bypass" in error_data.get("message", "").lower()

    @mock.patch("genesis_core.security.verifiers.firebase_app_check.app_check")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.credentials")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.os.path.exists")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.firebase_admin")
    def test_create_user_firebase_app_check_success(
        self, mock_firebase_admin, mock_exists, mock_credentials, mock_app_check, user_api,
        iam_client_with_firebase_app_check_rule
    ):
        mock_exists.return_value = True
        mock_cred = mock.MagicMock()
        mock_credentials.Certificate.return_value = mock_cred
        mock_app = mock.MagicMock()
        mock_firebase_admin.get_app.side_effect = ValueError("No app")
        mock_firebase_admin.initialize_app.return_value = mock_app
        mock_app_check.verify_token.return_value = {"app_id": "test-app-id"}
        headers = {"X-Firebase-AppCheck": "valid_firebase_token_12345"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_firebase_app_check_rule,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 200
        user_data = response.json()
        assert "name" in user_data or "username" in user_data
        assert "uuid" in user_data
        mock_app_check.verify_token.assert_called_once()

    @mock.patch("genesis_core.security.verifiers.firebase_app_check.app_check")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.credentials")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.os.path.exists")
    @mock.patch("genesis_core.security.verifiers.firebase_app_check.firebase_admin")
    def test_create_user_firebase_app_check_invalid_token_forbidden(
        self, mock_firebase_admin, mock_exists, mock_credentials, mock_app_check, user_api,
        iam_client_with_firebase_app_check_rule
    ):
        from firebase_admin import exceptions as firebase_exceptions
        mock_exists.return_value = True
        mock_cred = mock.MagicMock()
        mock_credentials.Certificate.return_value = mock_cred
        mock_app = mock.MagicMock()
        mock_firebase_admin.get_app.side_effect = ValueError("No app")
        mock_firebase_admin.initialize_app.return_value = mock_app
        mock_app_check.verify_token.side_effect = firebase_exceptions.InvalidArgumentError(
            "Invalid token"
        )
        headers = {"X-Firebase-AppCheck": "invalid_firebase_token_12345"}

        response = self._create_user_via_action(
            user_api,
            iam_client_with_firebase_app_check_rule,
            username=f"testuser_{sys_uuid.uuid4().hex[:8]}",
            password="testpass123",
            email=f"testuser_{sys_uuid.uuid4().hex[:8]}@example.com",
            headers=headers,
        )

        assert response.status_code == 403
        error_data = response.json()
        assert "CanNotCreateUser" in error_data.get("type", "")
        assert "firebase" in error_data.get("message", "").lower()
        mock_app_check.verify_token.assert_called_once()

