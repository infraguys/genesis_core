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

import bazooka

from gcl_sdk.clients.http import base
from gcl_sdk.agents.universal.drivers import direct
from gcl_sdk.agents.universal.storage import fs

from genesis_core.agent.universal.clients import rest as back


LOG = logging.getLogger(__name__)

AGENT_WORK_DIR = "/var/lib/genesis/universal_agent/"


class CoreCapabilityDriver(direct.DirectAgentDriver):
    """Core capability driver for interacting with Genesis Core."""

    def __init__(
        self,
        username: str,
        password: str,
        project_id: str,
        user_api_base_url: str,
        **collection_map,
    ):
        http = bazooka.Client()
        auth = base.CoreIamAuthenticator(
            user_api_base_url, username, password, http_client=http
        )
        self._collection_map = {
            k: v.strip() for k, v in collection_map.items()
        }

        rest_client = base.CollectionBaseClient(
            http_client=http, base_url=user_api_base_url, auth=auth
        )

        storage = fs.FileAgentStorage(AGENT_WORK_DIR)
        rest_client = back.GCRestApiBackendClient(
            rest_client, collection_map, project_id
        )

        super().__init__(storage=storage, client=rest_client)

    def get_capabilities(self) -> list[str]:
        """Returns a list of capabilities supported by the driver."""
        return list(self._collection_map.keys())
