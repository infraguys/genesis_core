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
from restalchemy.dm import types_network
from restalchemy.dm import types_dynamic
from restalchemy.dm import models as ra_models
from restalchemy.storage.sql import orm

from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.common.dm import models as cm
from genesis_core.secret import constants as sc


class AbstractSecretConstructor(
    types_dynamic.AbstractKindModel, ra_models.SimpleViewMixin
):

    def build(self, plain_secret: str) -> str:
        raise NotImplementedError()


class PlainSecretConstructor(AbstractSecretConstructor):
    KIND = "plain"

    def build(self, plain_secret: str) -> str:
        return plain_secret


class Secret(
    cm.ModelWithFullAsset,
    ua_models.TargetResourceMixin,
):
    status = properties.property(
        types.Enum([s.value for s in sc.SecretStatus]),
        default=sc.SecretStatus.NEW.value,
    )
    constructor = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(PlainSecretConstructor),
        ),
        required=True,
        default=PlainSecretConstructor,
    )


class Password(
    Secret,
    orm.SQLStorableMixin,
    ua_models.TargetResourceSQLStorableMixin,
):
    __tablename__ = "secret_passwords"

    method = properties.property(
        types.Enum([s.value for s in sc.SecretMethod]),
        default=sc.SecretMethod.AUTO_HEX.value,
    )
    value = properties.property(
        types.AllowNone(types.String(min_length=1, max_length=512)),
        default=None,
    )

    def get_resource_target_fields(self) -> set[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return {
            "method",
            "constructor",
            "name",
            "project_id",
            "uuid",
            "description",
        }

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
        return cls.get_deleted_target_resources(
            cls.__tablename__, sc.PASSWORD_KIND, limit
        )


class AbstractCertificateMethod(
    types_dynamic.AbstractKindModel, ra_models.SimpleViewMixin
):
    pass


class DNSCoreCertificateMethod(AbstractCertificateMethod):
    KIND = "dns_core"


class Certificate(
    Secret,
    orm.SQLStorableWithJSONFieldsMixin,
    ua_models.TargetResourceSQLStorableMixin,
):
    __tablename__ = "secret_certificates"
    __jsonfields__ = ["domains"]

    method = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(DNSCoreCertificateMethod),
        ),
        required=True,
        default=DNSCoreCertificateMethod,
    )
    expiration_at = properties.property(
        types.AllowNone(types.UTCDateTimeZ()),
        default=None,
    )
    email = properties.property(types.Email())
    domains = properties.property(
        types.TypedList(types_network.RecordNameWithWildcard()),
        required=True,
    )
    key = properties.property(
        types.AllowNone(types.String(min_length=1, max_length=10240)),
        default=None,
    )
    cert = properties.property(
        types.AllowNone(types.String(min_length=1, max_length=10240)),
        default=None,
    )
    # Count of days before expiration when the certificate should be renewed
    expiration_threshold = properties.property(
        types.Integer(min_value=0), default=14
    )
    # Two meanings:
    # - CP: ability to overcome the expiration threshold. `True` means it's
    #       possible to overcome and the certificate won't be renewed.
    # - DP: Is the threshold overcame?
    overcome_threshold = properties.property(types.Boolean(), default=False)

    def get_resource_target_fields(self) -> set[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return {
            "method",
            "email",
            "domains",
            "constructor",
            "name",
            "description",
            "project_id",
            "uuid",
            "expiration_threshold",
            "overcome_threshold",
        }

    @classmethod
    def get_new_certificates(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list["Certificate"]:
        return cls.get_new_entities(
            cls.__tablename__, sc.CERTIFICATE_KIND, limit
        )

    @classmethod
    def get_updated_certificates(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list["Certificate"]:
        return cls.get_updated_entities(
            cls.__tablename__, sc.CERTIFICATE_KIND, limit
        )

    @classmethod
    def get_deleted_certificates(
        cls, limit: int = sc.DEFAULT_SQL_LIMIT
    ) -> list[ua_models.TargetResource]:
        return cls.get_deleted_target_resources(
            cls.__tablename__, sc.CERTIFICATE_KIND, limit
        )
