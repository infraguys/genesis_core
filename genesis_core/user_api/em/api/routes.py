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

from genesis_core.user_api.em.api import controllers


class ManifestInstallActionRoute(routes.Action):
    """Handler for /v1/em/manifests/<uuid>/actions/install/invoke endpoint"""

    __controller__ = controllers.ManifestController


class ManifestUninstallActionRoute(routes.Action):
    """Handler for /v1/em/manifests/<uuid>/actions/uninstall/invoke endpoint"""

    __controller__ = controllers.ManifestController


class ManifestRoute(routes.Route):
    """Handler for /v1/em/manifests/ endpoint"""

    __controller__ = controllers.ManifestController

    install = routes.action(ManifestInstallActionRoute, invoke=True)
    uninstall = routes.action(ManifestUninstallActionRoute, invoke=True)


class ElementResourceRoute(routes.Route):
    """Handler for /v1/em/elements/<uuid>/resources/ endpoint"""

    __controller__ = controllers.ElementResourceController


class ElementRoute(routes.Route):
    """Handler for /v1/em/elements/<uuid>/ endpoint"""

    __controller__ = controllers.ElementController

    resources = routes.route(ElementResourceRoute, resource_route=True)


class ElementManagerRoute(routes.Route):
    """Handler for /v1/em/ endpoint"""

    __controller__ = controllers.ElementManagerController
    __allow_methods__ = [routes.FILTER]

    manifests = routes.route(ManifestRoute)
    elements = routes.route(ElementRoute)
