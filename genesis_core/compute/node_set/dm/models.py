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
from __future__ import annotations

import typing as tp
import uuid as sys_uuid

from genesis_core.compute import constants as nc
from genesis_core.compute.dm import models as compute_models


class Node(compute_models.Node):
    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "set_agent_node"


class NodeSet(compute_models.NodeSet):
    __derivative_model_map__ = {
        "set_agent_node": Node,
    }

    def create_nodes(
        self,
        project_id: sys_uuid.UUID,
        placement_policies: tp.Collection[
            compute_models.PlacementPolicy
        ] = tuple(),
    ) -> tp.Collection[Node]:
        """Create nodes for the node set."""
        nodes = []

        # NOTE(akremenetsky): Use the simplest implementation since we don't have
        # any node set type except the default one.
        for i in range(self.replicas):
            # This behavior is expected for the default node set type
            # but for other node set types it may need to be changed.
            node_uuid = sys_uuid.uuid5(self.uuid, f"node-{i}")
            node = Node(
                uuid=node_uuid,
                node_set=self.uuid,
                name=f"{self.name}-node-{str(node_uuid)[:4]}",
                cores=self.cores,
                ram=self.ram,
                root_disk_size=self.root_disk_size,
                image=self.image,
                project_id=project_id,
                node_type=self.node_type,
                status=nc.NodeStatus.NEW.value,
                placement_policies=[p.uuid for p in placement_policies],
            )
            nodes.append(node)

        return nodes
