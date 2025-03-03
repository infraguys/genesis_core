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
from restalchemy.api import resources
from restalchemy.storage import exceptions as ra_storage_exceptions

from genesis_core.node import constants as nc
from genesis_core.node.dm import models as node_models
from genesis_core.node.machine.dm import models as machine_models
from genesis_core.user_api.api import packers


class ApiEndpointController(controllers.RoutesListController):
    """Controller for /v1/ endpoint"""

    __TARGET_PATH__ = "/v1/"


class HealthController(controllers.Controller):
    """Controller for /v1/health/ endpoint"""

    def filter(self, filters):
        return "OK"


# Nodes


class NodesController(controllers.BaseResourceController):
    """Controller for /v1/nodes/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.Node,
        process_filters=True,
        convert_underscore=False,
    )


class MachinesController(controllers.BaseResourceController):
    """Controller for /v1/machines/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.Machine,
        process_filters=True,
        convert_underscore=False,
    )


class NetBootController(controllers.BaseResourceController):
    """Controller for /v1/boots/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.Netboot,
        process_filters=True,
        convert_underscore=False,
    )

    __packer__ = packers.IPXEPacker

    def get(self, uuid, **kwargs):
        try:
            base_netboot: node_models.Netboot = super().get(uuid, **kwargs)
            netboot = machine_models.Netboot.restore_from_simple_view(
                **base_netboot.dump_to_simple_view()
            )
        except ra_storage_exceptions.RecordNotFound:
            # Generate a dummy netboot object for netboot
            # configuration. Network is default option
            # for such machines.
            netboot = machine_models.Netboot(
                uuid=uuid,
                boot=nc.BootAlternative.network.value,
            )

        return netboot, 200, {"Content-Type": "application/octet-stream"}


class HypervisorsController(controllers.BaseResourceController):
    """Controller for /v1/hypervisors/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.MachinePool,
        process_filters=True,
        convert_underscore=False,
    )

    def create(self, **kwargs):
        hyper: node_models.MachinePool = self.model(**kwargs)

        if hyper.machine_type != nc.NodeType.VM:
            raise ValueError("Hyper must be VM type")

        hyper.insert()
        return hyper


class MachineAgentController(controllers.BaseResourceController):
    """Controller for /v1/machine_agents/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.MachineAgent,
        process_filters=True,
        convert_underscore=False,
    )
