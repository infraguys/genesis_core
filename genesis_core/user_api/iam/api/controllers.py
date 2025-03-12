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

import errno
from os import path as os_path
import mimetypes

from authlib.integrations import requests_client
import jinja2
from gcl_iam import controllers as iam_controllers
from restalchemy.api import actions
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.common import contexts
from restalchemy.openapi import utils as oa_utils

from genesis_core.user_api.iam.api import openapi_specs as oa_specs
from genesis_core.user_api.iam.clients import idp
from genesis_core.user_api.iam.dm import models
from genesis_core.user_api.iam import constants as c
from genesis_core.user_api.iam import exceptions as iam_e


class EnforceMixin:

    def enforce(self, rule, do_raise=False, exc=None):
        iam = contexts.get_context().iam_context
        return iam.enforcer.enforce(rule, do_raise, exc)


class IamController(controllers.RoutesListController):

    __TARGET_PATH__ = "/v1/iam/"


class UserController(controllers.BaseResourceController, EnforceMixin):
    __resource__ = resources.ResourceByModelWithCustomProps(
        models.User,
        convert_underscore=False,
        hidden_fields=resources.HiddenFieldMap(
            get=["salt", "secret_hash", "secret", "otp_secret"],
            create=["salt", "secret_hash", "otp_secret"],
            update=["salt", "secret_hash", "secret", "otp_secret"],
            filter=["salt", "secret_hash", "secret", "otp_secret"],
            action_post=["salt", "secret_hash", "secret", "otp_secret"],
        ),
        name_map={"secret": "password", "name": "username"},
    )

    def filter(self, filters):
        self.enforce(
            c.PERMISSION_USER_LISTING, do_raise=True, exc=iam_e.CanNotListUsers
        )
        return super().filter(filters)

    def update(self, uuid, **kwargs):
        is_me = models.User.me().uuid == uuid
        if self.enforce(c.PERMISSION_USER_WRITE_ALL) or is_me:
            return super().update(uuid, **kwargs)
        raise iam_e.CanNotUpdateUser(
            uuid=uuid, rule=c.PERMISSION_USER_WRITE_ALL
        )

    def delete(self, uuid):
        is_me = models.User.me().uuid == uuid
        if self.enforce(c.PERMISSION_USER_DELETE_ALL) or (
            is_me and self.enforce(c.PERMISSION_USER_DELETE)
        ):
            return super().delete(uuid)
        raise iam_e.CanNotDeleteUser(
            uuid=uuid,
            rule1=c.PERMISSION_USER_DELETE_ALL,
            rule2=c.PERMISSION_USER_DELETE,
        )

    @actions.post
    def change_password(self, resource, old_password, new_password):
        is_me = models.User.me() == resource
        if self.enforce(c.PERMISSION_USER_WRITE_ALL) or is_me:
            resource.change_secret_safe(
                old_secret=old_password,
                new_secret=new_password,
            )
            return resource
        raise iam_e.CanNotUpdateUser(
            uuid=resource.uuid, rule=c.PERMISSION_USER_WRITE_ALL
        )


class OrganizationController(
    iam_controllers.PolicyBasedWithoutProjectController,
    EnforceMixin,
):
    __resource__ = resources.ResourceByRAModel(
        models.Organization,
        convert_underscore=False,
    )
    __policy_service_name__ = "iam"
    __policy_name__ = "organization"

    def create(self, **kwargs):
        result = super().create(**kwargs)
        models.OrganizationMember(
            organization=result,
            user=models.User.me(),
            role=c.OrganizationRole.OWNER.value,
        ).insert()
        return result

    def filter(self, filters):
        pclass = iam_controllers.PolicyBasedWithoutProjectController
        if self.enforce(c.PERMISSION_ORGANIZATION_READ_ALL):
            return super(pclass, self).filter(filters)
        return models.Organization.list_my()

    def get(self, uuid, **kwargs):
        pclass = iam_controllers.PolicyBasedWithoutProjectController
        return super(pclass, self).get(uuid, **kwargs)

    def update(self, uuid, **kwargs):
        pclass = iam_controllers.PolicyBasedWithoutProjectController
        org = self.get(uuid)
        if org.are_i_owner() or self.enforce(
            c.PERMISSION_ORGANIZATION_WRITE_ALL
        ):
            return super(pclass, self).update(uuid, **kwargs)
        raise iam_e.CanNotUpdateOrganization(name=org.name)

    def delete(self, uuid):
        pclass = iam_controllers.PolicyBasedWithoutProjectController
        org = self.get(uuid)
        if self.enforce(c.PERMISSION_ORGANIZATION_DELETE_ALL):
            return super(pclass, self).delete(uuid)
        if org.are_i_owner():
            return super().delete(uuid)
        raise iam_e.CanNotDeleteOrganization(name=org.name)


class OrganizationMemberController(
    controllers.BaseResourceController, EnforceMixin
):
    __resource__ = resources.ResourceByRAModel(
        models.OrganizationMember,
        convert_underscore=False,
    )


class ProjectController(controllers.BaseResourceController, EnforceMixin):
    __resource__ = resources.ResourceByRAModel(
        models.Project,
        convert_underscore=False,
    )

    # def _check_create_project_in_organization(self, organization):
    #     user = models.User.my()
    #     if organization.owner != user:
    #         raise iam_e.CanNotCreateProjectInOrganization(
    #             name=organization.name,
    #         )

    # def _check_iam_organization_owner(self, organization):
    #     user = models.User.my()

    # def create(self, organization, **kwargs):
    #     self._check_create_project_in_organization(organization)
    #     return super().create(organization=organization, **kwargs)

    # def get(self, uuid, **kwargs):
    #     return super().get(uuid=uuid, **kwargs)


class RoleController(controllers.BaseResourceController, EnforceMixin):
    __resource__ = resources.ResourceByRAModel(
        models.Role,
        convert_underscore=False,
    )


class RoleBindingController(controllers.BaseResourceController, EnforceMixin):
    __resource__ = resources.ResourceByRAModel(
        models.RoleBinding,
        convert_underscore=False,
    )


class PermissionController(controllers.BaseResourceController, EnforceMixin):
    __resource__ = resources.ResourceByRAModel(
        models.Permission,
        convert_underscore=False,
    )


class PermissionBindingController(
    controllers.BaseResourceController, EnforceMixin
):
    __resource__ = resources.ResourceByRAModel(
        models.PermissionBinding,
        convert_underscore=False,
    )


class IdpController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByRAModel(
        models.Idp,
        convert_underscore=False,
    )

    def _get_request_params(self, resource):
        return {
            "idp_uuid": resource.uuid,
            "host_url": self._req.host_url,
        }

    def _build_oauth_session(self, resource):

        oauth_session = requests_client.OAuth2Session(
            client_id=resource.client_id,
            client_secret=resource.client_secret,
            redirect_uri=resource.get_redirect_uri(
                self._get_request_params(resource),
            ),
        )

        return oauth_session

    @actions.get
    def login(self, resource):
        idp_client = idp.IdpClient(resource.well_known_endpoint)
        metadata = idp_client.get_idp_metadata()

        oauth_session = self._build_oauth_session(resource)

        auth_url, _ = oauth_session.create_authorization_url(
            metadata["authorization_endpoint"],
            scope=resource.scope,
        )

        return None, 307, [("Location", auth_url)]

    @actions.get
    def callback(self, resource, state, session_state, iss, code):

        idp_client = idp.IdpClient(resource.well_known_endpoint)
        metadata = idp_client.get_idp_metadata()

        oauth_session = self._build_oauth_session(resource)
        token = oauth_session.fetch_token(
            metadata["token_endpoint"],
            code=code,
            authorization_response=resource.get_redirect_uri(
                self._get_request_params(resource),
            ),
        )
        return token


class ClientsController(controllers.BaseResourceController):
    __resource__ = resources.ResourceByModelWithCustomProps(
        models.IamClient,
        convert_underscore=False,
        hidden_fields=resources.HiddenFieldMap(
            get=["salt", "secret_hash", "secret"],
            create=["salt", "secret_hash"],
            update=["salt", "secret_hash"],
            filter=["salt", "secret_hash", "secret"],
        ),
    )

    @actions.get
    def auth(self, resource, **kwargs):
        login_url = (
            f"{self._req.host_url}/v1/iam/web/login/index.html?"
            + "&".join([f"{name}={value}" for name, value in kwargs.items()])
            + f"&client_uuid={resource.uuid}"
        )
        return None, 307, [("Location", login_url)]

    @actions.post
    def login(self, resource, user, password, **kwargs):
        # TODO(efrolov): rework this method. Is NOT working now
        raise NotImplementedError()

        # u = models.User.objects.get_one(filters={"name": user})
        # u.check_password(password)

        # redirect_uri = kwargs.get("redirect_uri", None)
        # if redirect_uri is not None:
        #     url = (
        #         redirect_uri
        #         + f"?state={kwargs['state']}"
        #         + "&session_state=96836906-d039-47e9-a321-f860d5224cb6"
        #         + "&code=cd3f2e5d-8ca5-4083-9344-2f8a4ea01f80.96836906"
        #         + "-d039-47e9-a321-f860d5224cb6.f5606e57-dfc9-4721-918"
        #         + "e-656182bb2f13"
        #         + "&iss=http%3A%2F%2Flocalhost%3A11010%2Fv1/%2FGenesis"
        #     )

        #     return None, 307, [("Location", url)]

        # return kwargs

    @oa_utils.extend_schema(**oa_specs.OA_SPEC_GET_TOKEN_KWARGS)
    @actions.post
    def get_token(self, resource, grant_type, **kwargs):
        if grant_type == c.GRANT_TYPE_PASSWORD:
            resource.validate_client_creds(
                client_id=kwargs.get(c.PARAM_CLIENT_ID),
                client_secret=kwargs.get(c.PARAM_CLIENT_SECRET),
            )
            token = resource.get_token_by_password(
                username=kwargs.get(c.PARAM_USERNAME),
                password=kwargs.get(c.PARAM_PASSWORD),
                scope=kwargs.get(c.PARAM_SCOPE, ""),
                root_endpoint=resource.redirect_url,
            )
            return token.get_response_body()
        elif grant_type == c.GRANT_TYPE_REFRESH_TOKEN:
            token = resource.get_token_by_refresh_token(
                refresh_token=kwargs.get("refresh_token"),
            )
            return token.get_response_body()
        else:
            raise iam_e.InvalidGrantType(grant_type=grant_type)

    @actions.get
    def introspect(self, resource):
        return contexts.get_context().iam_context.introspection_info()

    @actions.get
    def me(self, resource):
        return resource.me().get_response_body()


class WebController:

    def __init__(self, request):
        super().__init__()
        self._req = request

    def do_404(self):
        return self._req.ResponseClass(body="Not Found", status=404)

    def do(self, path, parent_resource=None, **kwargs):
        return self.do_404()

    @classmethod
    def get_resource(cls):
        return None


class IamWebController(WebController):

    TEMPLATE_DIR = os_path.abspath("web")

    ERROR_FILES = {
        404: "errors/404.html",
        500: "errors/500.html",
    }

    RENDER_FILES = [
        "login/index.html",
    ]

    def _get_file_body(self, full_path):
        with open(full_path, "rb") as fp:
            return fp.read()

    def _build_response(self, path, request_context=None):
        full_path = os_path.join(self.TEMPLATE_DIR, path)
        http_code = 500

        try:
            buff = self._get_file_body(full_path)
            if path in self.RENDER_FILES:
                buff = buff.decode("utf-8")
                buff = jinja2.Template(buff).render(**request_context)
                buff = buff.encode("utf-8")
            file_mimetype = mimetypes.guess_file_type(full_path)[0]
            http_code = 200
        except OSError as e:
            full_path = os_path.join(self.TEMPLATE_DIR, self.ERROR_FILES[500])
            if e.errno == errno.ENOENT:
                full_path = os_path.join(
                    self.TEMPLATE_DIR, self.ERROR_FILES[404]
                )
                http_code = 404
            buff = self._get_file_body(full_path)
            file_mimetype = mimetypes.guess_file_type(full_path)[0]
        except Exception:
            full_path = os_path.join(self.TEMPLATE_DIR, self.ERROR_FILES[500])
            buff = self._get_file_body(full_path)
            file_mimetype = mimetypes.guess_file_type(full_path)[0]

        return self._req.ResponseClass(
            body=buff,
            status=http_code,
            headerlist=[("Content-Type", file_mimetype)],
        )

    def _build_request_context(self):
        result = dict(self._req.params)
        result.update({"host_url": self._req.host_url})
        return result

    def do(self, path, parent_resource=None):
        request_context = self._build_request_context()
        return self._build_response(path.lstrip("/"), request_context)
