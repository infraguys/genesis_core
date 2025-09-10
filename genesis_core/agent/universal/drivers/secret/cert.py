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

from gcl_sdk.agents.universal.drivers import direct
from gcl_sdk.agents.universal.storage import fs
from gcl_sdk.clients.http import base as core_client_base
from gcl_certbot_plugin import clients as dns_clients

from genesis_core.agent.universal.drivers.secret.backend import (
    cert as cert_back,
)


LOG = logging.getLogger(__name__)

CERT_TARGET_FIELDS_STORAGE = (
    "/var/lib/genesis/genesis_core/cert_target_fields.json"
)


class CoreDNSCertificateCapabilityDriver(direct.DirectAgentDriver):
    """Certificate capability driver."""

    def __init__(
        self, user_api_base_url: str, username: str, password: str
    ) -> None:
        storage = fs.TargetFieldsFileStorage(CERT_TARGET_FIELDS_STORAGE)

        auth = core_client_base.CoreIamAuthenticator(
            base_url=user_api_base_url, username=username, password=password
        )
        dns_client = dns_clients.TinyDNSCoreClient(
            base_url=user_api_base_url, auth=auth
        )

        client = cert_back.CertBotBackendClient(
            dns_client, "admin@genesis-core.tech"
        )

        super().__init__(storage=storage, client=client)

    def get_capabilities(self) -> list[str]:
        """Returns a list of capabilities supported by the driver."""
        return ["certificate"]
