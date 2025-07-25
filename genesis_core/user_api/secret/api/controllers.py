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

from gcl_iam import controllers as iam_controllers
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.api import field_permissions as field_p
from restalchemy.api import constants as ra_c

from genesis_core.secret.dm import models
from genesis_core.secret import constants as sc


class SecretController(controllers.RoutesListController):

    __TARGET_PATH__ = "/v1/secret/"


class PasswordsController(iam_controllers.PolicyBasedController):
    """Controller for /v1/secret/passwords/ endpoint"""

    __policy_name__ = "password"
    __policy_service_name__ = "secret"

    __resource__ = resources.ResourceByRAModel(
        model_class=models.Password,
        process_filters=True,
        convert_underscore=False,
        fields_permissions=field_p.FieldsPermissions(
            default=field_p.Permissions.RW,
            fields={
                "status": {ra_c.ALL: field_p.Permissions.RO},
                "value": {ra_c.ALL: field_p.Permissions.RO},
            },
        ),
    )

    def update(self, uuid, **kwargs):
        # Force config to be NEW
        # In order to regenerate renders
        kwargs["status"] = sc.SecretStatus.NEW.value

        return super().update(uuid, **kwargs)


class CertificatesController(iam_controllers.PolicyBasedController):
    """Controller for /v1/secret/certificates/ endpoint"""

    __policy_name__ = "certificate"
    __policy_service_name__ = "secret"

    __resource__ = resources.ResourceByRAModel(
        model_class=models.Certificate,
        process_filters=True,
        convert_underscore=False,
        fields_permissions=field_p.FieldsPermissions(
            default=field_p.Permissions.RW,
            fields={
                "status": {ra_c.ALL: field_p.Permissions.RO},
                "key": {ra_c.ALL: field_p.Permissions.RO},
                "cert": {ra_c.ALL: field_p.Permissions.RO},
                "expiration_threshold": {ra_c.ALL: field_p.Permissions.HIDDEN},
                "overcome_threshold": {ra_c.ALL: field_p.Permissions.HIDDEN},
            },
        ),
    )

    def update(self, uuid, **kwargs):
        # Force config to be NEW
        # In order to regenerate renders
        kwargs["status"] = sc.SecretStatus.NEW.value

        return super().update(uuid, **kwargs)
