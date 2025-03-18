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

import abc
import uuid as sys_uuid

from bazooka import common
from bazooka import exceptions as bazooka_exc
import pytest
from restalchemy.api import constants as ra_api_c


class TestRequestContext:

    def __init__(
        self, response_id=None, request_body=None, params=None, headers=None
    ):
        super().__init__()
        self._resource_id = response_id
        self._request_body = request_body
        self._params = params
        self._headers = headers

    def _prepare_request_body(self, request_body, resource_id_name="uuid"):
        result = request_body.copy()
        if self._resource_id is not None:
            result[resource_id_name] = self._resource_id
        return result

    def get_request_body(self):
        return self._prepare_request_body(self._request_body)

    def get_params(self):
        return self._params

    def get_headers(self):
        return self._headers


class BaseIamResourceTest:

    def _has_role(self, roles, role_uuid):
        for role in roles:
            if role["uuid"] == role_uuid:
                return True
        return False


class StandardPermissionsTests(BaseIamResourceTest, metaclass=abc.ABCMeta):

    RESOURCE_UUID = str(sys_uuid.uuid4())

    TEST_RESOURCE = ""
    TEST_METHODS = {
        ra_api_c.CREATE: TestRequestContext(
            response_id=RESOURCE_UUID,
            request_body={},
        ),
        ra_api_c.GET: TestRequestContext(),
        ra_api_c.FILTER: TestRequestContext(),
        ra_api_c.UPDATE: TestRequestContext(
            response_id=RESOURCE_UUID,
            request_body={},
        ),
        ra_api_c.DELETE: TestRequestContext(
            response_id=RESOURCE_UUID,
        ),
    }

    def get_client_by_resource(self, client, path):
        result = client
        for pice in common.force_last_slash(path)[:-1].split("/"):
            result = getattr(result, pice)
        return result

    def get_target_client(self, client):
        return self.get_client_by_resource(
            client,
            self.TEST_RESOURCE,
        )

    def create_resource(self, client):
        target_client = self.get_target_client(client)
        ctx = self.TEST_METHODS[ra_api_c.CREATE]
        return target_client.create_response(
            body=ctx.get_request_body(),
            params=ctx.get_params(),
            headers=target_client.build_headers(headers=ctx.get_headers()),
        )

    def filter_resources(self, client):
        target_client = self.get_target_client(client)
        ctx = self.TEST_METHODS[ra_api_c.FILTER]
        return target_client.filter_response(
            params=ctx.get_params(),
            headers=target_client.build_headers(headers=ctx.get_headers()),
        )

    def get_resource(self, client):
        target_client = self.get_target_client(client)
        ctx = self.TEST_METHODS[ra_api_c.GET]
        return target_client.get_response(
            resource_id=ctx._resource_id,
            params=ctx.get_params(),
            headers=target_client.build_headers(headers=ctx.get_headers()),
        )

    def update_resource(self, client):
        target_client = self.get_target_client(client)
        ctx = self.TEST_METHODS[ra_api_c.UPDATE]
        return target_client.update_response(
            resource_id=ctx._resource_id,
            body=ctx.get_request_body(),
            params=ctx.get_params(),
            headers=target_client.build_headers(headers=ctx.get_headers()),
        )

    def delete_resource(self, client):
        target_client = self.get_target_client(client)
        ctx = self.TEST_METHODS[ra_api_c.UPDATE]
        return target_client.update_response(
            resource_id=ctx._resource_id,
            headers=target_client.build_headers(headers=ctx.get_headers()),
        )

    def _should_skip_test(self, test_method):
        if test_method not in self.TEST_METHODS:
            pytest.skip(
                f"Test {test_method} is not included in {self.TEST_METHODS}"
            )

    def test_create_resource_wo_auth(self, user_api_noauth_client):
        self._should_skip_test(ra_api_c.CREATE)
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            self.create_resource(client)

    def test_filter_resources_wo_auth(self, user_api_noauth_client):
        self._should_skip_test(ra_api_c.FILTER)
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            self.filter_resources(client)

    def test_get_resource_wo_auth(
        self, user_api_noauth_client, user_api_admin_client
    ):
        self._should_skip_test(ra_api_c.GET)
        # create resource
        self.create_resource(user_api_admin_client())
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            self.get_resource(client)

    def test_update_resource_wo_auth(
        self, user_api_noauth_client, user_api_admin_client
    ):
        self._should_skip_test(ra_api_c.UPDATE)
        # create resource
        self.create_resource(user_api_admin_client())
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            self.update_resource(client)

    def test_delete_resource_wo_auth(
        self, user_api_noauth_client, user_api_admin_client
    ):
        self._should_skip_test(ra_api_c.DELETE)
        # create resource
        self.create_resource(user_api_admin_client())
        client = user_api_noauth_client()

        with pytest.raises(bazooka_exc.UnauthorizedError):
            self.delete_resource(client)
