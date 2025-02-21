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
from restalchemy.api import controllers
from genesis_core.orch_api import versions


class RootController(controllers.Controller):
    """Controller for / endpoint"""

    def filter(self, filters):
        return [versions.API_VERSION_v1]


class ApiEndpointController(controllers.Controller):
    """Controller for /v1/ endpoint"""

    def filter(self, filters):
        return [
            "nodes",
            "sets",
            "elements",
            "configs",
            "artifacts",
            "services",
            "public_endpoints",
            "values",
            "profiles",
            "secrets",
        ]


class HealthController(controllers.Controller):
    """Controller for /v1/health/ endpoint"""

    def filter(self, filters):
        return "OK"
