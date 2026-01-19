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

import collections
import urllib.parse

import netaddr
from oslo_config import cfg
from gcl_iam import controllers as iam_controllers
from restalchemy.api import controllers as ra_controllers
from restalchemy.api import constants
from restalchemy.api import field_permissions as field_p
from restalchemy.api import resources

from genesis_core.user_api.dns.dm import models
from genesis_core.user_api.api import versions

CONF = cfg.CONF


class DnsController(ra_controllers.RoutesListController):

    __TARGET_PATH__ = "/v1/dns/"


class DomainController(
    iam_controllers.PolicyBasedController,
    ra_controllers.BaseResourceControllerPaginated,
):
    __policy_service_name__ = "dns"
    __policy_name__ = "domain"

    __resource__ = resources.ResourceByRAModel(
        models.Domain,
        convert_underscore=False,
        fields_permissions=field_p.FieldsPermissions(
            default=field_p.Permissions.RW,
            fields={
                "id": {constants.ALL: field_p.Permissions.HIDDEN},
            },
        ),
    )


class RecordController(
    iam_controllers.NestedPolicyBasedController,
    ra_controllers.BaseResourceControllerPaginated,
):
    __pr_name__ = "domain"
    __policy_service_name__ = "dns"
    __policy_name__ = "record"

    __resource__ = resources.ResourceByRAModel(
        models.Record,
        convert_underscore=False,
        fields_permissions=field_p.FieldsPermissions(
            default=field_p.Permissions.RW,
            fields={
                "domain_id": {constants.ALL: field_p.Permissions.HIDDEN},
                "name": {constants.ALL: field_p.Permissions.RO},
                "content": {constants.ALL: field_p.Permissions.HIDDEN},
            },
        ),
    )
