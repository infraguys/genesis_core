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
