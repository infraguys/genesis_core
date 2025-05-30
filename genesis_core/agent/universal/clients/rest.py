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

from gcl_sdk.agents.universal.dm import models
from gcl_sdk.clients.http import base as http
from gcl_sdk.agents.universal.clients.backend import rest

from genesis_core.agent.universal.clients import exceptions


class GCRestApiBackendClient(rest.RestApiBackendClient):
    """Genesis Core Rest API backend client."""

    def __init__(
        self,
        http_client: http.CollectionBaseClient,
        collection_map: dict[str:str],
        project_id: sys_uuid.UUID,
    ) -> None:
        super().__init__(
            http_client=http_client, collection_map=collection_map
        )
        self._project_id = str(project_id)

    def create(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Creates the resource. Returns the created resource."""
        # Inject mandatory fields
        resource.value["uuid"] = str(resource.uuid)

        # Simple validation for project_id. Only one project is supported.
        res_project_id = resource.value.get("project_id", None)
        if res_project_id and res_project_id != self._project_id:
            raise exceptions.ResourceProjectMismatch(resource=resource)

        return super().create(resource)

    def update(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Update the resource. Returns the updated resource."""
        # FIXME(akremenetsky): Not the best implementation
        # Remove popential RO fields
        value = resource.value.copy()
        value.pop("created_at", None)
        value.pop("updated_at", None)
        value.pop("project_id", None)
        value.pop("uuid", None)
        resource.value = value

        return super().update(resource)

    def list(self, kind: str) -> list[dict[str, tp.Any]]:
        """Lists all resources by kind."""
        return super().list(kind, project_id=self._project_id)
