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

from genesis_core.user_api.vs.api import controllers


class ProfilesActionRoute(routes.Action):
    """Handler for /v1/vs/profiles/<uuid>/actions/activate/invoke endpoint"""

    __controller__ = controllers.ProfilesController


class VariablesSelectValueRoute(routes.Action):
    """Handler for /v1/vs/variables/<uuid>/actions/select_value/invoke endpoint"""

    __controller__ = controllers.VariablesController


class VariablesReleaseValueRoute(routes.Action):
    """Handler for /v1/vs/variables/<uuid>/actions/release_value/invoke endpoint"""

    __controller__ = controllers.VariablesController


class ProfilesRoute(routes.Route):
    """Handler for /v1/vs/profiles/ endpoint"""

    __controller__ = controllers.ProfilesController

    activate = routes.action(ProfilesActionRoute, invoke=True)


class VariablesRoute(routes.Route):
    """Handler for /v1/vs/variables/ endpoint"""

    __controller__ = controllers.VariablesController

    select_value = routes.action(VariablesSelectValueRoute, invoke=True)
    release_value = routes.action(VariablesReleaseValueRoute, invoke=True)


class ValuesRoute(routes.Route):
    """Handler for /v1/vs/values/ endpoint"""

    __controller__ = controllers.ValuesController


class VSRoute(routes.Route):
    """Handler for /v1/vs/ endpoint"""

    __allow_methods__ = [routes.FILTER]
    __controller__ = controllers.ValuesStoreController

    profiles = routes.route(ProfilesRoute)
    variables = routes.route(VariablesRoute)
    values = routes.route(ValuesRoute)
