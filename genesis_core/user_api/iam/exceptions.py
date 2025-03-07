# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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

from gcl_iam import exceptions as iam_exc

from genesis_core.common import exceptions


class UserNotFound(exceptions.CommonNotFoundException):
    __template__ = "User with login {username} not found"


class CanNotSetOwner(exceptions.CommonForbiddenException, iam_exc.Forbidden):
    __template__ = (
        "The current user is not permitted to assign a different user as"
        " the owner. This action requires the `{rule}` permission, which is"
        " not granted. Please contact your administrator to request the"
        " necessary access or retain the current owner value."
    )


class CanNotListUsers(exceptions.CommonForbiddenException, iam_exc.Forbidden):
    __template__ = (
        "The current user is not permitted to list users. This action"
        " requires the `{rule}`, which has not been granted. Please contact"
        " your organization administrator to request access or use an"
        " account with the appropriate privileges."
    )


class CanNotCreateProjectInOrganization(
    exceptions.CommonForbiddenException,
    iam_exc.Forbidden,
):
    __template__ = (
        "The current user is not permitted to create a project in the"
        " organization `{name}`. Only the owner of the organization may"
        " create projects."
    )
