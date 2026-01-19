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
import contextlib
import datetime
from urllib import parse as urllib_parse

import pytest
import requests
from bazooka import exceptions as bazooka_exc
from gcl_iam.tests.functional import clients as iam_clients

from genesis_core.common import constants as common_c
from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam import constants as iam_c
from genesis_core.user_api.iam.dm import models as iam_models


class TestUsers(base.BaseIamResourceTest):

    USERS_ENDPOINT = "iam/users"

    @pytest.mark.parametrize("name", ["test", "Spider-Man"])
    def test_create_user_success(self, name, user_api_client, auth_user_admin):
        client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_USER_CREATE,
            ],
        )

        user = client.create_user(username=name, password="testtest")

        assert user["password"] == "*******"
        assert user["username"] == name

    def test_create_user_unauthenticated_fails(self, user_api_noauth_client):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            client.create_user(username="test_unauth", password="testtest")

    def test_create_user_no_permission_fails(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.create_user(username="test_no_perm", password="testtest")

    def test_create_user_400_error(self, user_api_client, auth_user_admin):
        client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_USER_CREATE,
            ],
        )

        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username="", password="test")
        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username="test400", password="test")
        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username="test400", password="test test")

    def test_create_user_space_login_400_error(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_USER_CREATE,
            ],
        )

        with pytest.raises(bazooka_exc.BadRequestError):
            client.create_user(username=" ", password="test")

    def test_create_user_without_first_last_name_success(
        self, user_api_client, auth_user_admin
    ):
        client = user_api_client(
            auth_user_admin,
            permissions=[
                iam_c.PERMISSION_USER_CREATE,
            ],
        )
        for empty_name in ["", None]:
            name = f"test_no_names_{empty_name}".lower()
            user = client.create_user(
                username=name,
                password="password",
                first_name=empty_name,
                last_name=empty_name,
            )
            assert user["username"] == name
            assert not user.get("first_name")
            assert not user.get("last_name")

    def test_update_user_clear_first_last_name_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)
        for empty_name in ["", None]:
            result = client.update_user(
                auth_test1_user.uuid,
                first_name=empty_name,
                last_name=empty_name,
            )
            assert result.get("first_name", None) == empty_name
            assert result.get("last_name", None) == empty_name

    def test_me_endpoint_with_empty_names_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(auth_test1_user)

        # First clear the names
        client.update_user(
            auth_test1_user.uuid,
            first_name="",
            last_name="",
        )

        # Verify in /me endpoint
        result = client.get(
            auth_test1_user.get_me_url(client.endpoint),
        ).json()

        assert result["user"]["first_name"] == ""
        assert result["user"]["last_name"] == ""

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
                iam_c.PERMISSION_USER_READ_ALL,
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
                iam_c.PERMISSION_USER_LISTING,
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
        name = "testXXX"
        result = client.update_user(auth_test1_user.uuid, username=name)
        assert result["username"] == name

    def test_update_other_user_test1_auth_forbidden(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(auth_test1_user)
        with pytest.raises(bazooka_exc.ForbiddenError):
            client.update_user(auth_test2_user.uuid, username="testXXX")

    def test_update_other_user_test1_auth_access(
        self, user_api_client, auth_test1_user, auth_test2_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                iam_c.PERMISSION_USER_WRITE_ALL,
            ],
        )
        name = "testXXX"
        result = client.update_user(auth_test2_user.uuid, username=name)
        assert result["username"] == name

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
                iam_c.PERMISSION_USER_WRITE_ALL,
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
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        user.email_verified = False
        user.create_confirmation_code()
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

    @pytest.mark.parametrize("code", ["invalid code", None])
    def test_confirm_email_invalid_code_400_error(
        self,
        user_api_noauth_client,
        auth_test1_user,
        code,
    ):
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.confirm_email(
                user_uuid=auth_test1_user.uuid,
                code=code,
            )

    @pytest.mark.parametrize(
        "code_made_at",
        [
            datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
            None,
        ],
    )
    def test_confirm_email_expired_code_400_error(
        self, user_api_noauth_client, auth_test1_user, code_made_at
    ):
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        user.email_verified = False
        user.create_confirmation_code()
        user.confirmation_code_made_at = code_made_at
        user.save()

        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.confirm_email(
                user_uuid=auth_test1_user.uuid,
                code=str(user.confirmation_code),
            )

    def test_delete_my_user_test1_auth_success(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                iam_c.PERMISSION_USER_DELETE,
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
                iam_c.PERMISSION_USER_DELETE_ALL,
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
                iam_c.PERMISSION_USER_DELETE,
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
            "username",
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

    @pytest.mark.parametrize(
        "grant_type, auth_param, expectation",
        [
            (iam_c.GRANT_TYPE_PASSWORD, "username", contextlib.nullcontext()),
            (
                iam_c.GRANT_TYPE_PASSWORD_USERNAME,
                "username",
                contextlib.nullcontext(),
            ),
            (
                iam_c.GRANT_TYPE_PASSWORD_EMAIL,
                "email",
                contextlib.nullcontext(),
            ),
            (
                iam_c.GRANT_TYPE_PASSWORD_PHONE,
                "phone",
                pytest.raises(bazooka_exc.BaseHTTPException),
                # auth by phone is not implemented yet
            ),
            ("invalid_grant_type", "username", pytest.raises(ValueError)),
            (
                iam_c.GRANT_TYPE_PASSWORD,
                "login",
                pytest.raises(bazooka_exc.BadRequestError),
            ),
            (
                iam_c.GRANT_TYPE_PASSWORD,
                "email",
                pytest.raises(bazooka_exc.BadRequestError),
            ),
            (
                iam_c.GRANT_TYPE_PASSWORD_EMAIL,
                "username",
                pytest.raises(bazooka_exc.BadRequestError),
            ),
            (
                iam_c.GRANT_TYPE_PASSWORD_LOGIN,
                "username",
                pytest.raises(bazooka_exc.BadRequestError),
            ),
        ],
    )
    def test_auth_with_param(
        self,
        grant_type,
        auth_param,
        expectation,
        user_api,
        auth_test1_user,
    ):
        params = {
            "username": None,
            "password": auth_test1_user.password,
            "grant_type": grant_type,
        }
        params[auth_param] = (getattr(auth_test1_user, auth_param, None),)
        auth = iam_clients.GenesisCoreAuth(**params)
        with expectation:
            client = iam_clients.GenesisCoreTestRESTClient(
                f"{user_api.get_endpoint()}v1/",
                auth,
            )  # tries to authorise on init
            assert "access_token" in client._auth_cache

    @pytest.mark.parametrize(
        "login, password, expectation",
        [
            ("username", None, contextlib.nullcontext()),
            ("email", None, contextlib.nullcontext()),
            ("phone", None, pytest.raises(bazooka_exc.BaseHTTPException)),
            ("username", "wrong", pytest.raises(bazooka_exc.BadRequestError)),
            ("username", "", pytest.raises(bazooka_exc.BadRequestError)),
            ("null", None, pytest.raises(bazooka_exc.BadRequestError)),
        ],
    )
    def test_auth_with_login(
        self,
        login,
        password,
        expectation,
        user_api,
        auth_test1_user,
    ):
        params = {
            "username": "dummy_username",
            "password": auth_test1_user.password,
            "grant_type": iam_c.GRANT_TYPE_PASSWORD_LOGIN,
            "login": getattr(auth_test1_user, login, "doesnt_exist"),
        }
        if password is not None:
            params["password"] = password

        auth = iam_clients.GenesisCoreAuth(**params)
        with expectation:
            client = iam_clients.GenesisCoreTestRESTClient(
                f"{user_api.get_endpoint()}v1/",
                auth,
            )  # tries to authorise on init
            assert "access_token" in client._auth_cache

    @pytest.mark.parametrize(
        "grant_type,use_email,field_name",
        [
            (iam_c.GRANT_TYPE_PASSWORD_USERNAME, False, "username"),
            (iam_c.GRANT_TYPE_PASSWORD_LOGIN, False, "login"),
            (iam_c.GRANT_TYPE_PASSWORD_LOGIN, True, "login"),
            (iam_c.GRANT_TYPE_PASSWORD_EMAIL, True, "email"),
        ],
    )
    def test_auth_case_insensitivity(
        self, user_api, auth_test1_user, grant_type, use_email, field_name
    ):
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        user.name = user.name.title()
        user.email = "Test1@mail.com"
        user.save()

        if use_email:
            login = user.email.upper()
        else:
            login = auth_test1_user.username.upper()

        params = {
            "username": None,
            "password": auth_test1_user.password,
            "grant_type": grant_type,
        }
        params[field_name] = login

        # Test authentication
        auth = iam_clients.GenesisCoreAuth(**params)
        client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth,
        )  # tries to authorise on init
        assert "access_token" in client._auth_cache

    def test_reset_password_success(
        self, auth_test1_user, user_api, default_client_uuid
    ):
        user = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        # after confirm email (auth_test1_user) confirmation_code is None
        assert user.confirmation_code is None

        url = urllib_parse.urljoin(
            user_api.base_url,
            f"iam/clients/{default_client_uuid}/actions/reset_password/invoke",
        )
        result = requests.post(url, json={"email": user.email})
        assert result.status_code == 200

        user_updated = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        # after send reset password event confirmation_code present
        assert user_updated.confirmation_code

        new_password = f"{auth_test1_user.password}_changed"
        url = urllib_parse.urljoin(
            user_api.base_url,
            f"iam/users/{user.uuid}/actions/reset_password/invoke",
        )
        result = requests.post(
            url,
            json={
                "new_password": new_password,
                "code": str(user_updated.confirmation_code),
            },
        )
        assert result.status_code == 200

        user_updated = iam_models.User.objects.get_one(
            filters={"uuid": auth_test1_user.uuid}
        )
        # after reset password confirmation_code is None
        assert user_updated.confirmation_code is None
        # password changed
        assert user_updated.secret_hash != user.secret_hash
