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
from datetime import timedelta

from gcl_iam import rules


# Grant Types
GRANT_TYPE_PASSWORD = "password"
GRANT_TYPE_PASSWORD_USERNAME = "username+password"
GRANT_TYPE_PASSWORD_EMAIL = "email+password"
GRANT_TYPE_PASSWORD_PHONE = "phone+password"
GRANT_TYPE_PASSWORD_LOGIN = "login+password"
GRANT_TYPE_REFRESH_TOKEN = "refresh_token"


# client parameters in request
PARAM_CLIENT_ID = "client_id"
PARAM_CLIENT_SECRET = "client_secret"

HEADER_CLIENT_ID = "X-Client-Id"
HEADER_CLIENT_SECRET = "X-Client-Secret"

HEADER_OTP_CODE = "X-OTP"


# user creds in request
PARAM_USERNAME = "username"
PARAM_EMAIL = "email"
PARAM_PHONE = "phone"
PARAM_LOGIN = "login"
PARAM_PASSWORD = "password"
PARAM_SCOPE = "scope"
PARAM_TTL = "ttl"
PARAM_REFRESH_TTL = "refresh_ttl"


# User settings
USER_CONFIRMATION_CODE_TTL = timedelta(hours=1)


# Default Values
PARAM_SCOPE_DEFAULT = ""


# Algorithms
ALGORITHM_HS256 = "HS256"


# Config section name
DOMAIN_IAM = "iam"
DOMAIN_IAM_TOKEN_HS256 = "token_hs256"


# Global Storage Keys
STORAGE_KEY_IAM_GLOBAL_SALT = "iam_global_salt"
STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM = "iam_token_encryption_algorithm"
STORAGE_KEY_IAM_TOKEN_HS256_ENCRYPTION_KEY = "iam_token_hs256_encryption_key"
STORAGE_KEY_EVENTS_CLIENT = "events_client"


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
# Users
PERMISSION_USER_LISTING = rules.Rule.from_raw(
    "iam.user.list",
)
PERMISSION_USER_READ_ALL = rules.Rule.from_raw(
    "iam.user.read_all",
)
PERMISSION_USER_WRITE_ALL = rules.Rule.from_raw(
    "iam.user.write_all",
)
PERMISSION_USER_DELETE_ALL = rules.Rule.from_raw(
    "iam.user.delete_all",
)
PERMISSION_USER_DELETE = rules.Rule.from_raw(
    "iam.user.delete",
)


# Organizations
PERMISSION_ORGANIZATION_CREATE = rules.Rule.from_raw(
    "iam.organization.create",
)
PERMISSION_ORGANIZATION_READ_ALL = rules.Rule.from_raw(
    "iam.organization.read_all",
)
PERMISSION_ORGANIZATION_WRITE_ALL = rules.Rule.from_raw(
    "iam.organization.write_all",
)
PERMISSION_ORGANIZATION_DELETE = rules.Rule.from_raw(
    "iam.organization.delete",
)
PERMISSION_ORGANIZATION_DELETE_ALL = rules.Rule.from_raw(
    "iam.organization.delete_all",
)


# Projects
PERMISSION_PROJECT_LIST_ALL = rules.Rule.from_raw(
    "iam.project.list_all",
)
PERMISSION_PROJECT_READ_ALL = rules.Rule.from_raw(
    "iam.project.read_all",
)
PERMISSION_PROJECT_WRITE_ALL = rules.Rule.from_raw(
    "iam.project.write_all",
)
PERMISSION_PROJECT_DELETE_ALL = rules.Rule.from_raw(
    "iam.project.delete_all",
)


# Permissions
PERMISSION_PERMISSION_CREATE = rules.Rule.from_raw(
    "iam.permission.create",
)
PERMISSION_PERMISSION_READ = rules.Rule.from_raw(
    "iam.permission.read",
)
PERMISSION_PERMISSION_UPDATE = rules.Rule.from_raw(
    "iam.permission.update",
)
PERMISSION_PERMISSION_DELETE = rules.Rule.from_raw(
    "iam.permission.delete",
)


# Permission bindings
PERMISSION_PERMISSION_BINDING_CREATE = rules.Rule.from_raw(
    "iam.permission_binding.create",
)
PERMISSION_PERMISSION_BINDING_READ = rules.Rule.from_raw(
    "iam.permission_binding.read",
)
PERMISSION_PERMISSION_BINDING_UPDATE = rules.Rule.from_raw(
    "iam.permission_binding.update",
)
PERMISSION_PERMISSION_BINDING_DELETE = rules.Rule.from_raw(
    "iam.permission_binding.delete",
)


# Roles
PERMISSION_ROLE_CREATE = rules.Rule.from_raw(
    "iam.role.create",
)
PERMISSION_ROLE_READ = rules.Rule.from_raw(
    "iam.role.read",
)
PERMISSION_ROLE_UPDATE = rules.Rule.from_raw(
    "iam.role.update",
)
PERMISSION_ROLE_DELETE = rules.Rule.from_raw(
    "iam.role.delete",
)


# Role bindings
PERMISSION_ROLE_BINDING_CREATE = rules.Rule.from_raw(
    "iam.role_binding.create",
)
PERMISSION_ROLE_BINDING_READ = rules.Rule.from_raw(
    "iam.role_binding.read",
)
PERMISSION_ROLE_BINDING_UPDATE = rules.Rule.from_raw(
    "iam.role_binding.update",
)
PERMISSION_ROLE_BINDING_DELETE = rules.Rule.from_raw(
    "iam.role_binding.delete",
)


# Iam Clients
PERMISSION_IAM_CLIENT_CREATE = rules.Rule.from_raw(
    "iam.iam_client.create",
)
PERMISSION_IAM_CLIENT_READ_ALL = rules.Rule.from_raw(
    "iam.iam_client.read_all",
)
PERMISSION_IAM_CLIENT_UPDATE = rules.Rule.from_raw(
    "iam.iam_client.update",
)
PERMISSION_IAM_CLIENT_DELETE = rules.Rule.from_raw(
    "iam.iam_client.delete",
)
