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
import os
import uuid as sys_uuid

GLOBAL_SERVICE_NAME = "genesis_core"
SERVICE_PROJECT_ID = sys_uuid.UUID("00000000-0000-0000-0000-000000000000")
EM_PROJECT_ID = sys_uuid.UUID("12345678-c625-4fee-81d5-f691897b8142")
EM_HIDDEN_PROJECT_ID = sys_uuid.UUID("12345670-6f3a-402e-acf8-0319d53eab58")
DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DEFAULT_SQL_LIMIT = 100

WORK_DIR = "/var/lib/genesis"
NODE_UUID_PATH = os.path.join(WORK_DIR, "node-id")

DEFAULT_USER_API_HOST = "127.0.0.1"
DEFAULT_USER_API_PORT = 11010
DEFAULT_ROOT_ENDPOINT = (
    f"http://{DEFAULT_USER_API_HOST}:{DEFAULT_USER_API_PORT}/v1/"
)

DEFAULT_GLOBAL_SALT = "FOy/2kwwdn0ig1QOq7cestqe"
DEFAULT_CLIENT_UUID = "00000000-0000-0000-0000-000000000000"
DEFAULT_CLIENT_ID = "GenesisCoreClientId"
DEFAULT_CLIENT_SECRET = "GenesisCoreSecret"
DEFAULT_HS256_JWKS_ENCRYPTION_KEY = (
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"


# Genesis Core Organization and Project Information
GENESIS_CORE_ORGANIZATION_UUID = "11111111-1111-1111-1111-111111111111"
GENESIS_CORE_ORGANIZATION_NAME = "Genesis Corporation"
GENESIS_CORE_ORGANIZATION_DESCRIPTION = (
    "The organization serves as the central platform for all services"
    " and elements developed by Genesis Corporation."
)


# Genesis Core Default Roles
NEWCOMER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000001"
NEWCOMER_ROLE_NAME = "newcomer"
NEWCOMER_ROLE_DESCRIPTION = (
    "Default role for newly registered users. Provides basic system access "
    "and onboarding capabilities."
)

OWNER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000002"
OWNER_ROLE_NAME = "owner"
OWNER_ROLE_DESCRIPTION = (
    "Project ownership role. Grants full administrative privileges "
    "within a specific project. Automatically assigned during project "
    "creation process."
)
