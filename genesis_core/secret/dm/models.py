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

from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from restalchemy.storage.sql import orm

from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.common.dm import models as cm
from genesis_core.secret import constants as sc


class PlainPasswordContainer(types_dynamic.AbstractKindModel):
    KIND = "plain"

    value = properties.property(
        types.AllowNone(types.String(min_length=1, max_length=256)),
        default=None,
    )


class Password(
    cm.ModelWithFullAsset,
    orm.SQLStorableMixin,
    ua_models.TargetResourceMixin,
    ua_models.TargetResourceSQLStorableMixin,
):
    __tablename__ = "secret_passwords"

    kind = properties.property(
        types.Enum([s.value for s in sc.SecretKind]),
        default=sc.SecretKind.AUTO.value,
    )
    status = properties.property(
        types.Enum([s.value for s in sc.SecretStatus]),
        default=sc.SecretStatus.NEW.value,
    )
    password = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(PlainPasswordContainer),
        ),
        required=True,
        default=PlainPasswordContainer,
    )

    @classmethod
    def get_new_passwords(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list["Password"]:
        return cls.get_new_entities(cls.__tablename__, sc.PASSWORD_KIND, limit)

    @classmethod
    def get_updated_passwords(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list["Password"]:
        return cls.get_updated_entities(
            cls.__tablename__, sc.PASSWORD_KIND, limit
        )

    @classmethod
    def get_deleted_passwords(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list[ua_models.TargetResource]:
        return cls.get_deleted_entities(
            cls.__tablename__, sc.PASSWORD_KIND, limit
        )
