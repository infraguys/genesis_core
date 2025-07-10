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

import pytest
from bazooka import exceptions as bazooka_exc

from genesis_core.common import constants as common_c
from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam import constants as c
from genesis_core.user_api.iam.dm import models as iam_models


class TestUsers(base.BaseIamResourceTest):

    USERS_ENDPOINT = "iam/users"

    def test_create_user_success(self, user_api_noauth_client):
        client = user_api_noauth_client()

        user = client.create_user(username="test", password="test")

        assert user["password"] == "*******"
        assert user["username"] == "test"

    def test_create_user_400_error(self, user_api_noauth_client):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username="", password="test")

    def test_create_user_space_login_400_error(self, user_api_noauth_client):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username=" ", password="test")

    def test_create_user_and_check_roles(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        roles = client.get_user_roles(auth_test1_user.uuid)

        assert self._has_role(roles, common_c.NEWCOMER_ROLE_UUID)

    def test_get_roles_another_user_success(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_READ_ALL,
            ],
        )

        roles = client.get_user_roles(auth_test2_user.uuid)

        assert len(roles) > 0

    def test_get_roles_another_user_forbidden(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.get_user_roles(auth_test2_user.uuid)

    def test_list_users_wo_auth_unauthorized(self, user_api_noauth_client):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.list_users()

    def test_list_users_admin_auth_success(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(auth_user_admin)

        result = client.list_users()

        assert isinstance(result, list)
        assert len(result) == 1

    def test_list_users_test1_auth_forbidden(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.list_users()

    def test_list_users_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth=auth_test1_user,
            permissions=[
                c.PERMISSION_USER_LISTING,
            ],
        )

        result = client.list_users()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_other_user_test1_auth_success(
        self, user_api_client, auth_test1_user, auth_user_admin
    ):
        client = user_api_client(auth_test1_user)

        result = client.get_user(auth_user_admin.uuid)

        assert result["uuid"] == auth_user_admin.uuid

    def test_update_my_user_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        result = client.update_user(
            auth_test1_user.uuid,
            username="testXXX",
        )

        assert result["username"] == "testxxx"

    def test_update_my_user_400_error(self, user_api_client, auth_test1_user):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.BadRequestError):
            client.update_user(
                auth_test1_user.uuid,
                first_name="",
            )

    def test_update_other_user_test1_auth_forbidden(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.update_user(
                auth_test2_user.uuid,
                username="testXXX",
            )

    def test_update_other_user_test1_auth_access(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_WRITE_ALL,
            ],
        )

        result = client.update_user(
            auth_test2_user.uuid,
            username="testXXX",
        )

        assert result["username"] == "testxxx"

    def test_update_my_user_update_password_test1_auth_bad_request(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.BadRequestError):
            client.update_user(
                auth_test1_user.uuid,
                password="new password",
            )

    def test_update_my_user_change_password_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        new_password = "new_password"
        client = user_api_client(auth_test1_user)

        result = client.change_user_password(
            uuid=auth_test1_user.uuid,
            old_password=auth_test1_user.password,
            new_password=new_password,
        )

        assert result["uuid"] == auth_test1_user.uuid

    def test_update_other_user_change_password_test1_auth_forbidden(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        new_password = "new_password"
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.change_user_password(
                uuid=auth_test2_user.uuid,
                old_password=auth_test2_user.password,
                new_password=new_password,
            )

    def test_update_other_user_change_password_test1_auth_success(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        new_password = "new_password"
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_WRITE_ALL,
            ],
        )

        result = client.change_user_password(
            uuid=auth_test2_user.uuid,
            old_password=auth_test2_user.password,
            new_password=new_password,
        )

        assert result["uuid"] == auth_test2_user.uuid

    def test_confirm_email_no_auth_success(
        self,
        user_api_noauth_client,
        auth_test1_user,
    ):
        user = iam_models.User.objects.get_one(filters={"uuid": auth_test1_user.uuid})
        user.email_verified = False
        user.confirmation_code = sys_uuid.uuid4()
        user.save()

        client = user_api_noauth_client()
        result = client.confirm_email(
            user_uuid=auth_test1_user.uuid,
            code=str(user.confirmation_code),
        )
        # Check for success in the API response
        assert result["uuid"] == str(auth_test1_user.uuid)
        assert result["email_verified"] is True

        # Check for success in the DB
        user_updated = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        assert user_updated.email_verified

    def test_confirm_email_invalid_code_400_error(
        self,
        user_api_noauth_client,
        auth_test1_user,
    ):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.confirm_email(
                user_uuid=auth_test1_user.uuid,
                code="invalid code",
            )

    def test_confirm_email_no_code_400_error(
        self, user_api_noauth_client, auth_test1_user
    ):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.confirm_email(
                user_uuid=auth_test1_user.uuid,
                code=None,
            )

    def test_delete_my_user_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_DELETE,
            ],
        )

        result = client.delete_user(auth_test1_user.uuid)

        assert result is None

    def test_delete_other_user_test1_auth_success(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_DELETE_ALL,
            ],
        )

        result = client.delete_user(auth_test2_user.uuid)

        assert result is None

    def test_delete_other_user_test1_auth_forbidden(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_USER_DELETE,
            ],
        )

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.delete_user(auth_test2_user.uuid)

    def test_fields_in_me_info_success(
        self,
        user_api_client,
        auth_test1_user,
    ):
        client = user_api_client(auth_test1_user)
        user_has_only_fields = [
            "uuid",
            "name",
            "description",
            "created_at",
            "updated_at",
            "status",
            "first_name",
            "last_name",
            "surname",
            "phone",
            "email",
            "otp_enabled",
            "email_verified",
        ]

        result = client.get(
            auth_test1_user.get_me_url(client.endpoint),
        ).json()

        for field in user_has_only_fields:
            result["user"].pop(field)
        assert result["user"] == {}
