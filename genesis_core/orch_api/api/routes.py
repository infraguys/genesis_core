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

from genesis_core.orch_api.api import controllers


class HealthRoute(routes.Route):
    """Handler for /v1/health endpoint"""

    __controller__ = controllers.HealthController
    __allow_methods__ = [routes.FILTER]


class NetbootRoute(routes.Route):
    """Handler for /v1/boots/ endpoint"""

    __controller__ = controllers.NetBootController
    __allow_methods__ = [routes.GET]


class NodeRoute(routes.Route):
    """Handler for /v1/nodes/ endpoint"""

    __controller__ = controllers.NodesController


class InterfacesRoute(routes.Route):
    """Handler for /v1/machines/<id>/interfaces/ endpoint"""

    __controller__ = controllers.InterfacesController


class MachineRoute(routes.Route):
    """Handler for /v1/machines/ endpoint"""

    __controller__ = controllers.MachinesController

    interfaces = routes.route(InterfacesRoute, resource_route=True)


class CoreAgentGetPayloadAction(routes.Action):
    """Handler for /v1/core_agents/<uuid>/actions/get_payload endpoint"""

    __controller__ = controllers.CoreAgentController


class CoreAgentRegisterPayloadAction(routes.Action):
    """Handler for /v1/core_agents/<uuid>/actions/register_payload/invoke endpoint"""

    __controller__ = controllers.CoreAgentController


class CoreAgentRoute(routes.Route):
    """Handler for /v1/core_agents/ endpoint"""

    __controller__ = controllers.CoreAgentController

    get_payload = routes.action(CoreAgentGetPayloadAction)
    register_payload = routes.action(
        CoreAgentRegisterPayloadAction, invoke=True
    )


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.ApiEndpointController
    __allow_methods__ = [routes.FILTER]

    health = routes.route(HealthRoute)
    boots = routes.route(NetbootRoute)
    nodes = routes.route(NodeRoute)
    machines = routes.route(MachineRoute)
    core_agents = routes.route(CoreAgentRoute)
