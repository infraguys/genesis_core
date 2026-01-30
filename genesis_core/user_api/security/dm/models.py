#    Copyright 2026 Genesis Corporation.
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

import abc
import enum
import re

from restalchemy.dm import models as ra_models
from restalchemy.dm import properties
from restalchemy.dm import types as ra_types
from restalchemy.dm import types_dynamic as ra_types_dynamic
from restalchemy.storage.sql import orm

from genesis_core.user_api.iam import constants as iam_c

# The http.HTTPMethod has all necessary methods, but it was added in 3.11
HTTP_METHODS = (
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
    "HEAD",
    "TRACE",
    "CONNECT",
)


class AbstractConditions(ra_types_dynamic.AbstractKindModel):
    @abc.abstractmethod
    def can_handle(self, context):
        raise NotImplementedError()


class UriConditions(AbstractConditions):
    KIND = "uri"

    uri = properties.property(
        ra_types.Uri(),
        required=True,
    )
    method = properties.property(
        ra_types.AllowNone(ra_types.Enum(HTTP_METHODS)),
        default=None,
    )

    def can_handle(self, context):
        request = context.request
        if self.method:
            if request.method.upper() != self.method:
                return False
        return request.path_info.lower() == self.uri.lower()


class UriRegexConditions(AbstractConditions):
    KIND = "uri_regex"

    uri_regex = properties.property(
        ra_types.String(),
        required=True,
    )
    method = properties.property(
        ra_types.AllowNone(ra_types.Enum(HTTP_METHODS)),
        default=None,
    )

    def can_handle(self, context):
        request = context.request
        if self.method:
            if request.method.upper() != self.method:
                return False
        return (
            re.match(
                self.uri_regex,
                request.path_info,
                flags=re.IGNORECASE,
            )
            is not None
        )


class AbstractVerifier(ra_types_dynamic.AbstractKindModel):

    @abc.abstractmethod
    def verify(self, context):
        raise NotImplementedError()


class FieldNotInRequestVerifier(AbstractVerifier):
    KIND = "no_fields"

    fields = properties.property(
        ra_types.TypedList(ra_types.String()),
        required=True,
    )

    def verify(self, context):
        payload = context.get_raw_payload()
        if not isinstance(payload, dict):
            return True
        json_keys = set(key.lower() for key in payload)
        return not any(field.lower() in json_keys for field in self.fields)


class OperatorEnum(str, enum.Enum):

    OR = "OR"
    AND = "AND"


class ModelWithAlwaysActiveStatus(ra_models.Model):

    STATUS = iam_c.AlwaysActiveStatus

    status = properties.property(
        ra_types.Enum([s.value for s in iam_c.AlwaysActiveStatus]),
        default=STATUS.ACTIVE.value,
    )


class Rule(
    ra_models.ModelWithUUID,
    ra_models.ModelWithNameDesc,
    ra_models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "security_rules"

    condition = properties.property(
        ra_types_dynamic.KindModelSelectorType(
            ra_types_dynamic.KindModelType(UriConditions),
            ra_types_dynamic.KindModelType(UriRegexConditions),
        ),
        required=True,
    )
    verifier = properties.property(
        ra_types_dynamic.KindModelSelectorType(
            ra_types_dynamic.KindModelType(FieldNotInRequestVerifier),
        ),
        required=True,
    )
    operator = properties.property(
        ra_types.Enum([s.value for s in OperatorEnum]),
        default=OperatorEnum.OR.value,
    )
    project_id = properties.property(
        ra_types.AllowNone(ra_types.UUID()),
        default=None,
        read_only=True,
    )

    def can_handle(self, context):
        return self.condition.can_handle(context)

    def verify(self, context):
        return self.verifier.verify(context)
