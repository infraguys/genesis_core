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
import typing as tp
import datetime

from restalchemy.dm import filters as dm_filters
from restalchemy.storage import exceptions as ra_exc
from gcl_sdk.agents.universal.dm import models
from gcl_sdk.agents.universal.clients.backend import base
from gcl_sdk.agents.universal.clients.backend import exceptions

from acme import client as acme_lib_client
from genesis_core.agent.universal.drivers.secret.backend import (
    clients as dns_clients,
)
from genesis_core.agent.universal.drivers.secret.backend import acme

from genesis_core.secret.dm import models as secret_dm
from genesis_core.agent.universal.drivers.secret.dm import models as driver_dm

LOG = logging.getLogger(__name__)


class CertBotBackendClient(base.AbstractBackendClient):
    """Cert bot backend client."""

    DEFAULT_PRIVATE_KEY_PATH = "/etc/genesis_core/certbot/privkey.pem"

    def __init__(
        self,
        dns_client: dns_clients.TinyDNSCoreClient,
        admin_email: str,
        private_key_path: str = DEFAULT_PRIVATE_KEY_PATH,
    ) -> None:
        self._dns_client = dns_client
        self._admin_email = admin_email
        self._client_acme: acme_lib_client.ClientV2 | None = None
        self._private_key = acme.get_or_create_client_private_key(
            private_key_path
        )

    @classmethod
    def _cert_to_value(cls, cert: driver_dm.Certificate) -> dict[str, tp.Any]:
        value = cert.meta
        value["key"] = cert.pkey
        value["cert"] = cert.fullchain
        return value

    def _get_or_create_acme_client(self) -> acme_lib_client.ClientV2:
        if self._client_acme is None:
            self._client_acme = acme.get_acme_client(
                self._private_key, self._admin_email
            )
        return self._client_acme

    def get(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Get the resource value in dictionary format."""
        try:
            cert = driver_dm.Certificate.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(resource.uuid),
                },
            )
        except ra_exc.RecordNotFound:
            raise exceptions.ResourceNotFound(resource=resource)

        return self._cert_to_value(cert)

    def create(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Creates the resource. Returns the created resource."""
        try:
            self.get(resource)
        except exceptions.ResourceNotFound:
            pass
        else:
            raise exceptions.ResourceAlreadyExists(resource=resource)

        cert = secret_dm.Certificate.from_ua_resource(resource)

        # Create cert via DNS
        # pkey_pem, csr_pem, fullchain_pem = acme.create_cert(
        #     self._get_or_create_acme_client(),
        #     self._dns_client,
        #     cert.domains,
        # )
        pkey_pem, csr_pem, fullchain_pem = (
            b"pkey_pem",
            b"csr_pem",
            "fullchain_pem",
        )
        expiration_at = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(days=90)

        # Build storagable password and save
        driver_cert = driver_dm.Certificate.from_cert_resource(
            resource, pkey_pem, csr_pem, fullchain_pem, expiration_at
        )

        driver_cert.save()
        return self._cert_to_value(cert)

    def update(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Update the resource. Returns the updated resource."""

        try:
            cert = driver_dm.Certificate.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(resource.uuid),
                },
            )
        except ra_exc.RecordNotFound:
            raise exceptions.ResourceNotFound(resource=resource)

        # TODO(akremenetsky): It's tricky logic to update the cert
        # if domains changed. Need to check domains intersection,
        # check wildcards
        if set(cert["meta"]["domains"]) != set(resource.value["domains"]):
            LOG.error("Not implemented yet")
            return self._cert_to_value(cert)

        # renew ?

    def list(self, kind: str, **kwargs) -> list[dict[str, tp.Any]]:
        """Lists all resources by kind."""
        certs = driver_dm.Certificate.objects.get_all()

        # Actualize some values
        for cert in certs:
            cert.meta["key"] = cert.pkey
            cert.meta["cert"] = cert.fullchain

        return [self._cert_to_value(cert) for cert in certs]

    def delete(self, resource: models.Resource) -> None:
        """Delete the resource."""
        try:
            self.get(resource)
        except exceptions.ResourceNotFound:
            raise exceptions.ResourceNotFound(resource=resource)

        cert = driver_dm.Certificate.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(resource.uuid),
            }
        )
        # acme.revoke_cert(self._get_or_create_acme_client(), cert.fullchain)
        cert.delete()
