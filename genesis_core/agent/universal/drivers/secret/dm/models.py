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

from restalchemy.dm import properties
from restalchemy.dm import models
from restalchemy.dm import types
from restalchemy.storage.sql import orm
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.secret import constants as sc
from genesis_core.secret.dm import models as secret_dm


class Password(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "storage_passwords"

    status = properties.property(
        types.Enum([s.value for s in sc.SecretStatus]),
        default=sc.SecretStatus.NEW.value,
    )
    value = properties.property(
        types.String(min_length=1, max_length=512),
        required=True,
    )
    # Some additional metadata about the secret
    meta = properties.property(types.Dict(), default=lambda: {})

    @classmethod
    def from_password_resource(
        cls, resource: ua_models.TargetResource, password_value: str
    ) -> Password:
        meta = resource.value.copy()
        meta["value"] = password_value
        meta["status"] = sc.SecretStatus.ACTIVE.value

        return cls(
            uuid=resource.uuid,
            value=password_value,
            status=sc.SecretStatus.ACTIVE.value,
            meta=meta,
        )
