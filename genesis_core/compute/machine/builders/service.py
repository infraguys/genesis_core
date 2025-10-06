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

import logging
import functools
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.agents.universal.services import builder as sdk_builder
from gcl_sdk.agents.universal.services import common as sdk_svc_common
from gcl_sdk.agents.universal.clients.orch import base as orch_base
from gcl_sdk.agents.universal.clients.orch import exceptions as orch_exc

from genesis_core.compute.dm import models
from genesis_core.common import utils
from genesis_core.compute import constants as nc

LOG = logging.getLogger(__name__)


class MachinePool(models.MachinePool, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "machine_pool"

    @classmethod
    def get_filter_clause(
        cls, builder: sys_uuid.UUID, pools: list[MachinePool]
    ) -> dict[str, dm_filters.AbstractClause] | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return {"builder": dm_filters.EQ(str(builder))}

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            ("uuid", "driver_spec", "machine_type", "cores_ratio", "ram_ratio")
        )


class MachineVolume(models.MachineVolume, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "machine_volume"

    @classmethod
    def get_filter_clause(
        cls, builder: sys_uuid.UUID, pools: list[MachinePool]
    ) -> dict[str, dm_filters.AbstractClause] | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return {"pool": dm_filters.In([p.uuid for p in pools])}

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "pool",
                "name",
                "index",
                "size",
                "image",
                "boot",
                "label",
                "device_type",
            )
        )


class Volume(models.Volume, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "volume"

    @classmethod
    def get_filter_clause(
        cls, builder: sys_uuid.UUID, pools: list[MachinePool]
    ) -> dict[str, dm_filters.AbstractClause] | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return {"pool": dm_filters.In([p.uuid for p in pools])}


class Node(models.Node, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "node"

    @classmethod
    def get_filter_clause(
        cls, builder: sys_uuid.UUID, pools: list[MachinePool]
    ) -> dict[str, dm_filters.AbstractClause] | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return {"pool": dm_filters.In([p.uuid for p in pools])}


class Machine(models.Machine, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "machine"

    @classmethod
    def get_filter_clause(
        cls, builder: sys_uuid.UUID, pools: list[MachinePool]
    ) -> dict[str, dm_filters.AbstractClause] | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return {"pool": dm_filters.In([p.uuid for p in pools])}


class PoolBuilderService(sdk_builder.CollectionUniversalBuilderService):

    def __init__(
        self,
        uuid: sys_uuid.UUID,
        orch_client: orch_base.AbstractOrchClient,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
    ) -> None:
        svc_spec = sdk_svc_common.UAServiceSpec(
            uuid=uuid,
            orch_client=orch_client,
            capabilities=(
                "builder_machine_pool",
                "builder_machine",
                "builder_machine_volume",
            ),
            name=f"compute_pool_builder {str(uuid)[:8]}",
        )

        super().__init__(
            instance_models=(
                MachinePool,
                Node,
                Machine,
                Volume,
                MachineVolume,
            ),
            service_spec=svc_spec,
            iter_min_period=iter_min_period,
            iter_pause=iter_pause,
        )

    def prepare_iteration(self) -> dict[str, tp.Any]:
        """Perform actions before iteration and return the iteration context.

        The result is a dictionary that is passed to the iteration context.
        """
        pools = models.MachinePool.objects.get_all(
            filters={
                "builder": dm_filters.EQ(str(self.ua_service_spec.uuid)),
            },
        )

        return {
            "clause_filters": {
                "builder": self.ua_service_spec.uuid,
                "pools": pools,
            }
        }

    def post_create_instance_resource(
        self,
        instance: MachinePool | Node | Machine | Volume | MachineVolume,
        resource: ua_models.TargetResource,
        derivatives: tp.Collection[ua_models.TargetResource] = tuple(),
    ) -> None:
        """The hook is performed after saving instance resource.

        The hook is called only for new instances.
        """
        # TODO(akremenetsky): Actually it's not enough to apply scheduling
        # info in this method. We need to apply it in the actualization
        # methods as well.

        super().post_create_instance_resource(instance, resource, derivatives)

        # Apply scheduing info to the target resource
        if hasattr(instance, "agent"):
            resource.agent = instance.agent
        elif instance_pool := getattr(instance, "pool", None):
            for pool in self._iteration_context["clause_filters"]["pools"]:
                if pool.uuid == instance_pool:
                    resource.agent = pool.agent
                    break

    def actualize_outdated_instance(
        self,
        current_instance: (
            MachinePool | Node | Machine | Volume | MachineVolume
        ),
        actual_instance: MachinePool | Node | Machine | Volume | MachineVolume,
    ) -> None:
        """Actualize outdated instance.

        It means some changes occurred on the data plane and the instance
        is outdated now. For example, the instance `Password` has field
        `value` that is stored in the secret storage. If the value is changed
        or created on the data plane, the instance is outdated and this method
        is called to reactualize the instance.

        Args:
            current_instance: The current instance.
            actual_instance: The actual instance.
        """
        self.actualize_outdated_instance_dispatch(
            current_instance,
            actual_instance,
        )

        current_instance.status = actual_instance.status

    @functools.singledispatchmethod
    def actualize_outdated_instance_dispatch(
        self,
        current_instance: (
            MachinePool | Node | Machine | Volume | MachineVolume
        ),
        actual_instance: MachinePool | Node | Machine | Volume | MachineVolume,
    ) -> None:
        raise TypeError(f"Unsupported type: {type(current_instance)}")

    @actualize_outdated_instance_dispatch.register
    def _(
        self, current_instance: MachinePool, actual_instance: MachinePool
    ) -> None:
        current_instance.all_cores = actual_instance.all_cores
        current_instance.all_ram = actual_instance.all_ram
        current_instance.avail_cores = actual_instance.avail_cores
        current_instance.avail_ram = actual_instance.avail_ram
        current_instance.storage_pool_map = actual_instance.storage_pool_map

    @actualize_outdated_instance_dispatch.register
    def _(self, current_instance: Machine, actual_instance: Machine) -> None:
        pass

    @actualize_outdated_instance_dispatch.register
    def _(self, current_instance: Volume, actual_instance: Volume) -> None:
        pass

    @actualize_outdated_instance_dispatch.register
    def _(
        self, current_instance: MachineVolume, actual_instance: MachineVolume
    ) -> None:
        pass

    @actualize_outdated_instance_dispatch.register
    def _(self, current_instance: Node, actual_instance: Node) -> None:
        pass
