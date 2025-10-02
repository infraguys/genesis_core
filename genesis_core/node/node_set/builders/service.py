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

import logging
import uuid as sys_uuid
import typing as tp

from gcl_sdk.infra.services import builder

from genesis_core.node.node_set.dm import models
from genesis_core.node import constants as nc

LOG = logging.getLogger(__name__)


class NodeSetBuilder(builder.CoreInfraBuilder):

    def __init__(
        self,
        instance_model: tp.Type[models.NodeSet],
        project_id: sys_uuid.UUID,
    ):
        super().__init__(instance_model)
        self._project_id = project_id

    def create_infra(
        self, instance: models.NodeSet
    ) -> tp.Collection[models.Node]:
        """Create a list of infrastructure objects.

        The method returns a list of infrastructure objects that are required
        for the instance. For example, nodes, sets, configs, etc.
        """
        return instance.create_nodes(self._project_id)

    def actualize_infra(
        self,
        instance: models.NodeSet,
        infra: builder.InfraCollection,
    ) -> tp.Collection[models.Node]:
        """Actualize the infrastructure objects.

        The method is called when the instance is outdated. For example,
        the instance `Config` has derivative `Render`. Single `Config` may
        have multiple `Render` derivatives. If any of the derivatives is
        outdated, this method is called to reactualize this infrastructure.

        Args:
            instance: The instance to actualize.
            infra: The infrastructure objects.
        """
        actual_nodes = {}
        statuses = []
        status = instance.status

        # Get the target nodes for the node set based on the current
        # configuration. This will be used to filter out nodes that are
        # being deleted during a shrink operation.
        new_target_nodes = {
            n.uuid: n for n in instance.create_nodes(self._project_id)
        }

        for _, actual in infra.infra_objects:
            if actual is None:
                continue

            # Skip the nodes that are not in the target nodes.
            # They will be deleted.
            if actual.uuid not in new_target_nodes:
                continue

            uuid_str = str(actual.uuid)
            actual_nodes[uuid_str] = {}

            if ipv4 := actual.default_network.get("ipv4"):
                actual_nodes[uuid_str]["ipv4"] = ipv4

            statuses.append(actual.status)

        instance.nodes = actual_nodes

        # Set the status to active if all nodes are active.
        # It's normal to compare the length of statuses with replicas
        # for the default node set type.
        if len(statuses) >= instance.replicas and all(
            s == nc.NodeStatus.ACTIVE for s in statuses
        ):
            status = nc.NodeStatus.ACTIVE.value
        elif any(s == nc.NodeStatus.ERROR for s in statuses):
            status = nc.NodeStatus.ERROR.value
        elif any(s == nc.NodeStatus.NEW for s in statuses):
            status = nc.NodeStatus.NEW.value
        elif any(s == nc.NodeStatus.IN_PROGRESS for s in statuses):
            status = nc.NodeStatus.IN_PROGRESS.value

        if status != instance.status:
            instance.status = status

        return tuple(new_target_nodes.values())
