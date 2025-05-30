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

from restalchemy.api import routes

from genesis_core.user_api.dns.api import controllers


class RecordsRoute(routes.Route):
    """Handler for /v1/dns/<id>/records/ endpoint"""

    __controller__ = controllers.RecordController


class DomainsRoute(routes.Route):
    """Handler for /v1/dns/domains/ endpoint"""

    __controller__ = controllers.DomainController

    records = routes.route(RecordsRoute, resource_route=True)


class DnsRoute(routes.Route):
    """Handler for /v1/dns/ endpoint"""

    __controller__ = controllers.DnsController
    __allow_methods__ = [routes.FILTER]

    domains = routes.route(DomainsRoute)
