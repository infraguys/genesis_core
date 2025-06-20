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

import secrets
import logging
import typing as tp

from restalchemy.dm import filters as dm_filters
from restalchemy.storage import exceptions as ra_exc
from gcl_sdk.agents.universal.dm import models
from gcl_sdk.agents.universal.clients.backend import base
from gcl_sdk.agents.universal.clients.backend import exceptions

from genesis_core.secret import constants as sc
from genesis_core.secret.dm import models as secret_dm
from genesis_core.agent.universal.drivers.secret.dm import models as driver_dm


LOG = logging.getLogger(__name__)


class DatabaseSecretBackendClient(base.AbstractBackendClient):
    """Secret Backend client based on SQL database."""

    def get(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Get the resource value in dictionary format."""
        try:
            driver_password = driver_dm.Password.objects.get_one(
                filters={
                    "uuid": dm_filters.EQ(resource.uuid),
                },
            )
        except ra_exc.RecordNotFound:
            raise exceptions.ResourceNotFound(resource=resource)

        return driver_password.meta

    def create(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Creates the resource. Returns the created resource."""
        try:
            self.get(resource)
        except exceptions.ResourceNotFound:
            pass
        else:
            raise exceptions.ResourceAlreadyExists(resource=resource)

        password = secret_dm.Password.from_ua_resource(resource)

        # Validate structure of password model
        if (
            sc.SecretMethod[password.method].is_auto
            and password.value is not None
        ):
            raise ValueError("Cannot create auto-generated password.")

        if (
            not sc.SecretMethod[password.method].is_auto
            and password.value is None
        ):
            raise ValueError("Cannot create non-auto-generated password.")

        # Generate plain password
        if sc.SecretMethod[password.method].is_auto:
            if password.method == sc.SecretMethod.AUTO_HEX:
                plain_password = secrets.token_hex(16)
            elif password.method == sc.SecretMethod.AUTO_URL_SAFE:
                plain_password = secrets.token_urlsafe(16)
            else:
                raise ValueError("Unknown auto-generated password method.")
        else:
            plain_password = password.value

        # Build password from the plain view
        pass_value = password.constructor.build(plain_password)

        # Build storagable password and save
        driver_password = driver_dm.Password.from_password_resource(
            resource, pass_value
        )
        driver_password.save()
        return driver_password.meta

    def update(self, resource: models.Resource) -> dict[str, tp.Any]:
        """Update the resource. Returns the updated resource."""

        # The simplest implementation. Update via recreation.
        self.delete(resource)
        return self.create(resource)

    def list(self, kind: str, **kwargs) -> list[dict[str, tp.Any]]:
        """Lists all resources by kind."""
        secrets = driver_dm.Password.objects.get_all()
        return [s.meta for s in secrets]

    def delete(self, resource: models.Resource) -> None:
        """Delete the resource."""
        try:
            self.get(resource)
        except exceptions.ResourceNotFound:
            raise exceptions.ResourceNotFound(resource=resource)

        password = driver_dm.Password.objects.get_one(
            filters={
                "uuid": dm_filters.EQ(resource.uuid),
            }
        )
        password.delete()
