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
from genesis_core.user_api.dns.api import routes as dns_routes
from genesis_core.user_api.em.api import routes as em_routes
from genesis_core.user_api.iam.api import routes as iam_routes
from genesis_core.user_api.config.api import routes as config_routes
from genesis_core.user_api.secret.api import routes as secret_routes
from genesis_core.user_api.compute.api import routes as compute_routes


# TODO(e.frolov): should be raw route
class HealthRoute(routes.Route):
    """Handler for /v1/health endpoint"""

    __controller__ = controllers.HealthController
    __allow_methods__ = [routes.FILTER]


# DEPRECATED(akremenetsky): Use compute route
class NodeRoute(routes.Route):
    """Handler for /v1/nodes/ endpoint"""

    __controller__ = controllers.NodesController


# DEPRECATED(akremenetsky): Use compute route
class MachineRoute(routes.Route):
    """Handler for /v1/machines/ endpoint"""

    __controller__ = controllers.MachinesController


# DEPRECATED(akremenetsky): Use compute route
class HypervisorRoute(routes.Route):
    """Handler for /v1/hypervisors/ endpoint"""

    __controller__ = controllers.HypervisorsController


# DEPRECATED(akremenetsky): Use compute route
# class MachineAgentRoute(routes.Route):
#     """Handler for /v1/machine_agents/ endpoint"""

#     __controller__ = controllers.MachineAgentController


# DEPRECATED(akremenetsky): Use compute route
class NodeSetsRoute(routes.Route):
    """Handler for /v1/sets/ endpoint"""

    __controller__ = controllers.NodeSetsController


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.ApiEndpointController
    __allow_methods__ = [routes.FILTER]

    dns = routes.route(dns_routes.DnsRoute)
    health = routes.route(HealthRoute)
    iam = routes.route(iam_routes.IamRoute)
    em = routes.route(em_routes.ElementManagerRoute)
    config = routes.route(config_routes.ConfigRoute)
    secret = routes.route(secret_routes.SecretRoute)
    compute = routes.route(compute_routes.ComputeRoute)

    # DEPRECATED(akremenetsky): Use compute route
    nodes = routes.route(NodeRoute)
    machines = routes.route(MachineRoute)
    hypervisors = routes.route(HypervisorRoute)
    # machine_agents = routes.route(MachineAgentRoute)
    sets = routes.route(NodeSetsRoute)
