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

from genesis_core.user_api.compute.api import controllers


class VolumeAttachActionRoute(routes.Action):
    """Handler for /v1/compute/volumes/<uuid>/actions/attach/invoke endpoint"""

    __controller__ = controllers.VolumesController


class VolumeDetachActionRoute(routes.Action):
    """Handler for /v1/compute/volumes/<uuid>/actions/detach/invoke endpoint"""

    __controller__ = controllers.VolumesController


class VolumesRoute(routes.Route):
    """Handler for /v1/compute/volumes/ endpoint"""

    __controller__ = controllers.VolumesController

    attach = routes.action(VolumeAttachActionRoute, invoke=True)
    detach = routes.action(VolumeDetachActionRoute, invoke=True)


class NodeRoute(routes.Route):
    """Handler for /v1/compute/nodes/ endpoint"""

    __controller__ = controllers.NodesController


# class MachineRoute(routes.Route):
#     """Handler for /v1/compute/machines/ endpoint"""

#     __controller__ = controllers.MachinesController


class HypervisorRoute(routes.Route):
    """Handler for /v1/compute/hypervisors/ endpoint"""

    __controller__ = controllers.HypervisorsController


# class MachineAgentRoute(routes.Route):
#     """Handler for /v1/compute/machine_agents/ endpoint"""

#     __controller__ = controllers.MachineAgentController


class NodeSetsRoute(routes.Route):
    """Handler for /v1/compute/sets/ endpoint"""

    __controller__ = controllers.NodeSetsController


class ComputeRoute(routes.Route):
    """Handler for /v1/compute/ endpoint"""

    __allow_methods__ = [routes.FILTER]
    __controller__ = controllers.ComputeController

    volumes = routes.route(VolumesRoute)
    nodes = routes.route(NodeRoute)
    # machines = routes.route(MachineRoute)
    hypervisors = routes.route(HypervisorRoute)
    # machine_agents = routes.route(MachineAgentRoute)
    sets = routes.route(NodeSetsRoute)
