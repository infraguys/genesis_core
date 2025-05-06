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
import datetime
import uuid as sys_uuid

import bazooka

from genesis_core.agents.clients import base
from genesis_core.agents.dm import models
from genesis_core.orch_api.dm import models as orch_models
from genesis_core.node.dm import models as node_models
from genesis_core.common import constants as c


class InterfacesClient(base.CollectionBaseModelClient):
    __collection_url__ = "/interfaces/"
    __model__ = node_models.Interface
    __parent__ = "machine"


class MachineClient(base.ResourceBaseModelClient):
    __model__ = models.Machine

    @property
    def interfaces(self):
        return InterfacesClient(
            base_url=self.resource_url(), http_client=self._http_client
        )


class MachinesClient(base.CollectionBaseModelClient):
    __collection_url__ = "/v1/machines/"
    __model__ = models.Machine
    __resource_client__ = MachineClient


class NodesClient(base.CollectionBaseModelClient):
    __collection_url__ = "/v1/nodes/"
    __model__ = models.Node


class RendersClient(base.CollectionBaseModelClient):
    __collection_url__ = "/v1/renders/"
    __model__ = orch_models.OrchRenderModel


class CoreAgentsClient(base.CollectionBaseModelClient):
    __collection_url__ = "/v1/core_agents/"
    __model__ = models.CoreAgent

    def get_target_payload(
        self, uuid: sys_uuid.UUID, dp_payload: models.Payload
    ) -> models.Payload:
        payload_updated_at = datetime.datetime.strftime(
            dp_payload.payload_updated_at,
            c.DEFAULT_DATETIME_FORMAT,
        )
        payload_data = self.do_action(
            "get_payload",
            uuid,
            payload_hash=dp_payload.payload_hash,
            payload_updated_at=payload_updated_at,
        )
        return models.Payload.restore_from_simple_view(**payload_data)

    def register_payload(
        self, uuid: sys_uuid.UUID, dp_payload: models.Payload
    ) -> None:
        dp_payload.update_payload_hash()
        state = dp_payload.dump_to_simple_view()
        self.do_action("register_payload", uuid, invoke=True, **state)


class OrchAPI:
    def __init__(
        self,
        base_url: str,
        http_client: bazooka.Client | None = None,
    ) -> None:
        http_client = http_client or bazooka.Client()

        self._http_client = http_client
        self._machines_client = MachinesClient(base_url, http_client)
        self._nodes_client = NodesClient(base_url, http_client)
        self._agents_client = CoreAgentsClient(base_url, http_client)
        self._renders_client = RendersClient(base_url, http_client)

    @property
    def machines(self):
        return self._machines_client

    @property
    def nodes(self):
        return self._nodes_client

    @property
    def agents(self):
        return self._agents_client

    @property
    def renders(self):
        return self._renders_client
