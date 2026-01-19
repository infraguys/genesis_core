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

import typing as tp
import logging

from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.paas.dm import services as srv_models

from genesis_core.elements.dm import models

LOG = logging.getLogger(__name__)


class ServiceNode(
    srv_models.Service,
    ua_models.TargetResourceKindAwareMixin,
    ua_models.SchedulableToAgentFromAgentUUIDMixin,
):
    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "service_agent_node"

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "name",
                "path",
                "user",
                "group",
                "service_type",
                "before",
                "after",
                "target_status",
            )
        )


class Service(
    models.Service,
    ua_models.InstanceWithDerivativesMixin,
):

    # __master_model__ = sdk_models.NodeSet
    __derivative_model_map__ = {
        "service_agent_node": ServiceNode,
    }

    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "service_agent"

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "path",
            )
        )
