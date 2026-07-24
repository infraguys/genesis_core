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

from gcl_iam.api import controllers as iam_controllers
from restalchemy.api import controllers as ra_controllers
from restalchemy.api import resources
from restalchemy.dm import types

from exordos_core.quota.dm import models


class QuotaController(ra_controllers.RoutesListController):
    __TARGET_PATH__ = "/v1/quota/"


class QuotaLimitController(
    iam_controllers.PolicyBasedController,
    ra_controllers.BaseResourceControllerPaginated,
):
    __policy_service_name__ = "quota"
    __policy_name__ = "limit"

    __resource__ = resources.ResourceByRAModel(
        models.QuotaLimit,
        process_filters=True,
        convert_underscore=False,
    )

    @staticmethod
    def _validate_quota_field(resource_name, field_name):
        resource_model = models.get_quota_resource_model(resource_name)
        if not field_name:
            return

        quota_property = resource_model.properties.properties.get(field_name)
        if quota_property is None:
            raise ValueError(f"Unknown quota field: {field_name}")
        if not isinstance(
            quota_property.get_property_type(), (types.Integer, types.Float)
        ):
            raise TypeError(f"Quota field must be an integer: {field_name}")

    def create(self, **kwargs):
        self._validate_quota_field(
            kwargs["resource_name"],
            kwargs.get("field_name", ""),
        )
        return super().create(**kwargs)

    def update(self, uuid, **kwargs):
        quota_limit = self.get(uuid=uuid)
        self._validate_quota_field(
            kwargs.get("resource_name", quota_limit.resource_name),
            kwargs.get("field_name", quota_limit.field_name),
        )
        return super().update(uuid, **kwargs)
