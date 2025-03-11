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

import enum

from gcl_iam import rules


# Grant Types
GRANT_TYPE_PASSWORD = "password"
GRANT_TYPE_REFRESH_TOKEN = "refresh_token"


# client parameters in request
PARAM_CLIENT_ID = "client_id"
PARAM_CLIENT_SECRET = "client_secret"


# user creds in request
PARAM_USERNAME = "username"
PARAM_PASSWORD = "password"
PARAM_SCOPE = "scope"


# Default Values
PARAM_SCOPE_DEFAULT = "openid, project:default"


# Algorithms
ALGORITHM_HS256 = "HS256"


# Config section name
DOMAIN_IAM = "iam"
DOMAIN_IAM_TOKEN_HS256 = "token_hs256"


# Global Storage Keys
STORAGE_KEY_IAM_GLOBAL_SALT = "iam_global_salt"
STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM = "iam_token_encryption_algorithm"
STORAGE_KEY_IAM_TOKEN_HS256_ENCRYPTION_KEY = "iam_token_hs256_encryption_key"


class OwnerType(str, enum.Enum):
    NEW = "USER"
    SCHEDULED = "SERVICE"


class Status(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ACTIVE = "ACTIVE"


class AlwaysActiveStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"


class OrganizationRole(str, enum.Enum):
    MEMBER = "MEMBER"
    OWNER = "OWNER"


# permissions

# Organizations
ORGANIZATION_CHANGE_OWNER = rules.Rule.from_raw(
    "iam.organization.change_owner",
)

# Users
PERMISSION_USER_LISTING = rules.Rule.from_raw(
    "iam.user.list",
)
