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

from gcl_sdk.agents.universal.orch_api import routes as orch_routes
from genesis_core.orch_api.api import controllers


class HealthRoute(routes.Route):
    """Handler for /v1/health endpoint"""

    __controller__ = controllers.HealthController
    __allow_methods__ = [routes.FILTER]


class NetbootRoute(routes.Route):
    """Handler for /v1/boots/ endpoint"""

    __controller__ = controllers.NetBootController
    __allow_methods__ = [routes.GET]


# class NodeRoute(routes.Route):
#     """Handler for /v1/nodes/ endpoint"""

#     __controller__ = controllers.NodesController


# class MachineRoute(routes.Route):
#     """Handler for /v1/machines/ endpoint"""

#     __controller__ = controllers.MachinesController


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.ApiEndpointController
    __allow_methods__ = [routes.FILTER]

    health = routes.route(HealthRoute)
    boots = routes.route(NetbootRoute)
    # nodes = routes.route(NodeRoute)
    # machines = routes.route(MachineRoute)
    agents = routes.route(orch_routes.UniversalAgentsRoute)
