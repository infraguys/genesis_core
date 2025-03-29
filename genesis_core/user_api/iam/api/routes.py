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

from genesis_core.user_api.iam.api import controllers


class WebRoute(routes.Route):

    def do(self, parent_resource=None):
        controller = self.get_controller(self._req)
        return controller.do(
            path=self._req.path_info, parent_resource=parent_resource
        )


class ChangePasswordAction(routes.Action):
    """Handler for .../users/<uuid>/actions/change_password/invoke endpoint"""

    __controller__ = controllers.UserController


class EnableOTPAction(routes.Action):
    """Handler for .../users/<uuid>/actions/enable_otp/invoke endpoint"""

    __controller__ = controllers.UserController


class ActivateOTPAction(routes.Action):
    """Handler for .../users/<uuid>/actions/activate_otp/invoke endpoint"""

    __controller__ = controllers.UserController


class DisableOTPAction(routes.Action):
    """Handler for .../users/<uuid>/actions/disable_otp/invoke endpoint"""

    __controller__ = controllers.UserController


class GetMyRolesAction(routes.Action):
    """Handler for .../users/<uuid>/actions/get_my_roles endpoint"""

    __controller__ = controllers.UserController


class UserRoute(routes.Route):
    """Handler for /v1/iam/users/ endpoint"""

    __controller__ = controllers.UserController

    change_password = routes.action(ChangePasswordAction, invoke=True)
    enable_otp = routes.action(EnableOTPAction, invoke=True)
    activate_otp = routes.action(ActivateOTPAction, invoke=True)
    disable_otp = routes.action(DisableOTPAction, invoke=True)
    get_my_roles = routes.action(GetMyRolesAction)


class OrganizationController(routes.Route):
    """Handler for /v1/iam/organizations/ endpoint"""

    __controller__ = controllers.OrganizationController


class OrganizationMemberRoute(routes.Route):
    """Handler for /v1/iam/organization_members/<uuid>/members/ endpoint"""

    __controller__ = controllers.OrganizationMemberController


class ProjectRoute(routes.Route):
    """Handler for /v1/iam/projects/ endpoint"""

    __controller__ = controllers.ProjectController


class RoleRoute(routes.Route):
    """Handler for /v1/iam/roles/ endpoint"""

    __controller__ = controllers.RoleController


class RoleBindingRoute(routes.Route):
    """Handler for /v1/iam/role_bindings/ endpoint"""

    __controller__ = controllers.RoleBindingController


class PermissionRoute(routes.Route):
    """Handler for /v1/iam/permissions/ endpoint"""

    __controller__ = controllers.PermissionController


class PermissionBindingRoute(routes.Route):
    """Handler for /v1/iam/permission_bindings/ endpoint"""

    __controller__ = controllers.PermissionBindingController


class LoginAction(routes.Action):
    """Handler for /v1/iam/idp/<uuid>/actions/login/invoke endpoint"""

    __controller__ = controllers.IdpController


class CallbackAction(routes.Action):
    """Handler for /v1/iam/idp/<uuid>/actions/callback/invoke endpoint"""

    __controller__ = controllers.IdpController


class IdpRoute(routes.Route):
    """Handler for /v1/iam/idp/ endpoint"""

    __controller__ = controllers.IdpController

    login = routes.action(LoginAction, invoke=True)
    callback = routes.action(CallbackAction, invoke=True)


class AuthAction(routes.Action):
    """Handler for /v1/iam/clients/<uuid>/actions/auth/invoke endpoint"""

    __controller__ = controllers.ClientsController


class loginAction(routes.Action):
    """Handler for /v1/iam/clients/<uuid>/actions/login/invoke endpoint"""

    __controller__ = controllers.ClientsController


class GetTokenAction(routes.Action):
    """Handler for /v1/iam/clients/<uuid>/actions/get_token/invoke endpoint"""

    __controller__ = controllers.ClientsController


class IntrospectAction(routes.Action):
    """Handler for /v1/iam/clients/<uuid>/actions/introspection endpoint"""

    __controller__ = controllers.ClientsController


class MeAction(routes.Action):
    """Handler for /v1/iam/clients/<uuid>/actions/me endpoint"""

    __controller__ = controllers.ClientsController


class IamClientsRoute(routes.Route):
    """Handler for /v1/iam/clients/ endpoint"""

    __controller__ = controllers.ClientsController

    auth = routes.action(AuthAction, invoke=True)
    login = routes.action(loginAction, invoke=True)
    get_token = routes.action(GetTokenAction, invoke=True)
    introspect = routes.action(IntrospectAction)
    me = routes.action(MeAction)


class IamWebRoute(WebRoute):
    __controller__ = controllers.IamWebController
    __allow_methods__ = []


class IamRoute(routes.Route):
    """Handler for /v1/iam/ endpoint"""

    __allow_methods__ = [routes.FILTER]
    __controller__ = controllers.IamController

    # main resources
    users = routes.route(UserRoute)
    organizations = routes.route(OrganizationController)
    organization_members = routes.route(OrganizationMemberRoute)
    projects = routes.route(ProjectRoute)
    roles = routes.route(RoleRoute)
    role_bindings = routes.route(RoleBindingRoute)
    permissions = routes.route(PermissionRoute)
    permission_bindings = routes.route(PermissionBindingRoute)

    # oauth2, oidc, sso, etc
    idp = routes.route(IdpRoute)
    clients = routes.route(IamClientsRoute)
    web = routes.route(IamWebRoute)
