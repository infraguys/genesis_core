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

import abc
import logging
import typing as tp
import uuid as sys_uuid

from gcl_sdk.agents.universal.dm import models
from gcl_sdk.agents.universal.clients.backend import base
from gcl_sdk.agents.universal.clients.backend import exceptions


LOG = logging.getLogger(__name__)

AGENT_WORK_DIR = "/var/lib/genesis/universal_agent/"


class DatabaseSecretBackendClient(base.AbstractBackendClient):
    """Secret Backend client based on SQL database."""

    def get(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Get the resource value in dictionary format."""

    def create(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Creates the resource. Returns the created resource."""

    def update(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Update the resource. Returns the updated resource."""

    def list(self, kind: str, **kwargs) -> list[dict[str, tp.Any]]:
        """Lists all resources by kind."""

    def delete(self, resource: models.Resource) -> None:
        """Delete the resource."""
