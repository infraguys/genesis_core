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

from restalchemy.api import routes

from genesis_core.user_api.api import controllers
from genesis_core.user_api.em.api import routes as em_routes
from genesis_core.user_api.iam.api import routes as iam_routes
from genesis_core.user_api.config.api import routes as config_routes


# TODO(e.frolov): should be raw route
class HealthRoute(routes.Route):
    """Handler for /v1/health endpoint"""

    __controller__ = controllers.HealthController
    __allow_methods__ = [routes.FILTER]


class NodeRoute(routes.Route):
    """Handler for /v1/nodes/ endpoint"""

    __controller__ = controllers.NodesController


class MachineRoute(routes.Route):
    """Handler for /v1/machines/ endpoint"""

    __controller__ = controllers.MachinesController


class HypervisorRoute(routes.Route):
    """Handler for /v1/hypervisors/ endpoint"""

    __controller__ = controllers.HypervisorsController


class MachineAgentRoute(routes.Route):
    """Handler for /v1/machine_agents/ endpoint"""

    __controller__ = controllers.MachineAgentController


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.ApiEndpointController
    __allow_methods__ = [routes.FILTER]

    health = routes.route(HealthRoute)
    iam = routes.route(iam_routes.IamRoute)
    em = routes.route(em_routes.ElementManagerRoute)
    config = routes.route(config_routes.ConfigRoute)
    nodes = routes.route(NodeRoute)
    machines = routes.route(MachineRoute)
    hypervisors = routes.route(HypervisorRoute)
    machine_agents = routes.route(MachineAgentRoute)
