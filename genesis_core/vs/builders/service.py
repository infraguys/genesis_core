#    Copyright 2025-2026 Genesis Corporation.
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

import logging
import uuid as sys_uuid
import typing as tp

from gcl_sdk.infra import exceptions as infra_exc
from gcl_sdk.agents.universal import constants as ua_c
from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.agents.universal.services import builder as sdk_builder
from gcl_sdk.agents.universal.clients.orch import base as orch_base

from genesis_core.vs.dm import models

LOG = logging.getLogger(__name__)


class Profile(
    models.Profile,
    ua_models.InstanceMixin,
):
    pass


class Value(
    models.Value,
    ua_models.InstanceMixin,
):
    pass


class Variable(
    models.Variable,
    ua_models.InstanceMixin,
):
    __tracked_instances_model_map__ = {
        "vs_profile": Profile,
    }

    def get_tracked_resources(
        self,
    ) -> tp.Collection[ua_models.RI]:
        """Return the tracked resources.

        Method returns either collection of ResourceKindAwareMixin or
        ResourceIdentifier. If any of resources are changed, a special hooks
        in the UB will be called to actualize the instance.
        """
        if isinstance(self.setter, models.ProfileVariableSetter):
            return tuple(
                ua_models.RI("vs_profile", p["profile"])
                for p in self.setter.profiles
            )

        return tuple()


class VSBuilderService(sdk_builder.CollectionUniversalBuilderService):

    def __init__(
        self,
        uuid: sys_uuid.UUID,
        orch_client: orch_base.AbstractOrchClient,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
    ) -> None:
        super().__init__(
            instance_models=(Profile, Value, Variable),
            iter_min_period=iter_min_period,
            iter_pause=iter_pause,
        )

    # Internal methods

    # Builder lifecycle hooks

    def post_create_instance_resource(
        self,
        instance: ua_models.InstanceMixin,
        resource: ua_models.TargetResource,
        derivatives: tp.Collection[ua_models.TargetResource] = tuple(),
    ) -> None:
        """The hook is performed after saving instance resource.

        The hook is called only for new instances.
        """
        # Skip Profile and Value instances
        if not isinstance(instance, Variable):
            return

        variable: Variable = instance
        try:
            variable.setter.set_value(variable)
            variable.status = ua_c.InstanceStatus.ACTIVE.value
        except infra_exc.VariableCannotFindValue:
            # Undefine the variable if it cannot be determined
            variable.value = None
            variable.status = ua_c.InstanceStatus.IN_PROGRESS.value

    def post_update_instance_resource(
        self,
        instance: models.InstanceMixin,
        resource: models.TargetResource,
        derivatives: tp.Collection[models.TargetResource] = tuple(),
    ) -> None:
        """The hook is performed after updating instance resource."""
        # Skip Profile and Value instances
        if not isinstance(instance, Variable):
            return

        variable: Variable = instance
        try:
            variable.setter.set_value(variable)
            variable.status = ua_c.InstanceStatus.ACTIVE.value
        except infra_exc.VariableCannotFindValue:
            # Undefine the variable if it cannot be determined
            variable.value = None
            variable.status = ua_c.InstanceStatus.IN_PROGRESS.value

    def actualize_instance_with_outdated_tracked(
        self,
        instance: Variable,
        tracked_instances: tp.Collection[Profile],
    ) -> None:
        """Actualize instance with outdated tracked instances.

        This method is used to actualize a particular instance with outdated
        tracked instances. See `_actualize_instances_with_outdated_tracked`
        for more details.

        Args:
            instance: The instance to actualize.
            tracked_instances: The tracked instances that are changed.
        """
        variable: Variable = instance
        try:
            variable.setter.set_value(variable)
            variable.status = ua_c.InstanceStatus.ACTIVE.value
        except infra_exc.VariableCannotFindValue:
            # Undefine the variable if it cannot be determined
            variable.value = None
            variable.status = ua_c.InstanceStatus.IN_PROGRESS.value
