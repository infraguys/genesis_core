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
from restalchemy.api import constants as ra_c
from restalchemy.api import field_permissions as field_p


from genesis_core.compute import constants as nc
from genesis_core.compute.dm import models as node_models
from genesis_core.user_api.compute.dm import models as user_models


class ComputeController(controllers.RoutesListController):

    __TARGET_PATH__ = "/v1/compute/"


class NodesController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/compute/nodes/ endpoint"""

    __policy_name__ = "node"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=user_models.Node,
        process_filters=True,
        convert_underscore=False,
    )


class NodeSetsController(iam_controllers.PolicyBasedController):
    """Controller for /v1/compute/sets/ endpoint"""

    __policy_name__ = "node_set"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.NodeSet,
        process_filters=True,
        convert_underscore=False,
        fields_permissions=field_p.FieldsPermissions(
            default=field_p.Permissions.RW,
            fields={
                "status": {ra_c.ALL: field_p.Permissions.RO},
                "nodes": {ra_c.ALL: field_p.Permissions.RO},
            },
        ),
    )

    def update(self, uuid, **kwargs):
        # Force config to be NEW
        # In order to regenerate renders
        kwargs["status"] = nc.NodeStatus.NEW.value

        return super().update(uuid, **kwargs)


class MachinesController(
    iam_controllers.PolicyBasedController,
    controllers.BaseResourceControllerPaginated,
):
    """Controller for /v1/compute/machines/ endpoint"""

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
    """Controller for /v1/compute/hypervisors/ endpoint"""

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
    """Controller for /v1/compute/machine_agents/ endpoint"""

    __policy_name__ = "machine_agent"
    __policy_service_name__ = nc.POLICY_SERVICE_NAME

    __resource__ = resources.ResourceByRAModel(
        model_class=node_models.MachineAgent,
        process_filters=True,
        convert_underscore=False,
    )
