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

WORK_DIR = "/var/lib/genesis"
NODE_UUID_PATH = os.path.join(WORK_DIR, "node-id")

DEFAULT_USER_API_HOST = "127.0.0.1"
DEFAULT_USER_API_PORT = 11010

DEFAULT_GLOBAL_SALT = "FOy/2kwwdn0ig1QOq7cestqe"
DEFAULT_CLIENT_UUID = "00000000-0000-0000-0000-000000000000"
DEFAULT_CLIENT_ID = "GenesisCoreClientId"
DEFAULT_CLIENT_SECRET = "GenesisCoreSecret"
DEFAULT_HS256_KEY = "secret"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
