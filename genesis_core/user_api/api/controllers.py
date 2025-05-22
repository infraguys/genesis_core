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

from gcl_iam import controllers as iam_controllers
from restalchemy.api import controllers
from restalchemy.api import resources

from genesis_core.node import constants as nc
from genesis_core.node.dm import models as node_models


class ApiEndpointController(controllers.RoutesListController):
    """Controller for /v1/ endpoint"""

    __TARGET_PATH__ = "/v1/"


class HealthController(controllers.Controller):
    """Controller for /v1/health/ endpoint"""

    def filter(self, filters, **kwargs):
        return "OK"


# Nodes


class NodesController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/nodes/ endpoint"""

    __policy_name__ = "node"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.Node,
        process_filters=True,
        convert_underscore=False,
    )


class MachinesController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/machines/ endpoint"""

    __policy_name__ = "machine"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.Machine,
        process_filters=True,
        convert_underscore=False,
    )


class HypervisorsController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/hypervisors/ endpoint"""

    __policy_name__ = "hypervisor"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

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


class MachineAgentController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/machine_agents/ endpoint"""

    __policy_name__ = "machine_agent"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.MachineAgent,
        process_filters=True,
        convert_underscore=False,
    )
