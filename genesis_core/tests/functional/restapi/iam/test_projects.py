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

from genesis_core.common import constants as common_c
from genesis_core.tests.functional.restapi.iam import base
from genesis_core.user_api.iam import constants as c


class TestProjects(base.BaseIamResourceTest):

    def test_create_user_and_check_roles(
        self, user_api_client, auth_test1_user
    ):
        client = user_api_client(
            auth_test1_user,
            permissions=[
                c.PERMISSION_ORGANIZATION_CREATE,
            ],
        )
        org = client.create_organization(
            name="TestOrganization",
        )

        client.create_project(
            name="TestProject",
            organization_uuid=org["uuid"],
        )

        roles = client.get_user_roles(auth_test1_user.uuid)
        assert self._has_role(roles, common_c.OWNER_ROLE_UUID)
