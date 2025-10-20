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
import uuid as sys_uuid
import typing as tp

from restalchemy.common import contexts
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.dm import filters as dm_filters
from restalchemy.storage.sql import filters as sql_filters
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
        cls, builder: sys_uuid.UUID, pools: tuple[sys_uuid.UUID, ...]
    ) -> sql_filters.AbstractClause | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return dm_filters.EQ(value=str(builder))
        # return sql_filters.EQ(column="builder", value=str(builder))


class Machine(models.Machine, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "machine"

    @classmethod
    def get_filter_clause(
        cls, pools: tuple[sys_uuid.UUID, ...]
    ) -> sql_filters.AbstractClause | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return None


class MachineVolume(models.MachineVolume, ua_models.InstanceMixin):

    @classmethod
    def get_resource_kind(cls) -> str:
        return "machine_volume"

    @classmethod
    def get_filter_clause(
        cls, pools: tuple[sys_uuid.UUID, ...]
    ) -> sql_filters.AbstractClause | None:
        """Get filter clause for the instance model.

        The clause is returned back to the service to take a chance for
        the service enrich the clause. After that the clause is used in
        the database queries. The service haven't must call method
        `get_new_instances` and other with the clause if it was returned.
        It depends on the service implementation.
        """
        return None


class PoolBuilderService(sdk_svc_common.CollectionUniversalBuilderService):

    def __init__(
        self,
        uuid: sys_uuid.UUID,
        orch_client: orch_base.AbstractOrchClient,
        iter_min_period: int = 1,
        iter_pause: float = 0.1,
    ) -> None:
        svc_spec = sdk_svc_common.ServiceSpec(
            uuid=uuid,
            orch_client=orch_client,
            capabilities=(
                "builder_machine_pool",
                "builder_machine",
                "builder_machine_volume",
            ),
        )

        super().__init__(
            instance_models=(MachinePool, Machine, MachineVolume),
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
                "builder": dm_filters.EQ(str(self.uuid)),
            },
        )

        return {
            "clause_filters": {
                "builder": self.uuid,
                "pools": tuple(p.uuid for p in pools),
            }
        }
