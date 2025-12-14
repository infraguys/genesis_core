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

from gcl_iam import middlewares as iam_mw
from restalchemy.api import applications
from restalchemy.api import constants as ra_c
from restalchemy.api import middlewares
from restalchemy.api import routes
from restalchemy.api.middlewares import logging as logging_mw
from restalchemy.dm import types as ra_types
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import engines as openapi_engines

from genesis_core.common.api.middlewares import errors as errors_mw
from genesis_core.user_api.api import routes as app_routes
from genesis_core.user_api.api import versions
from genesis_core.user_api.iam import drivers
from genesis_core import version


skip_auth_endpoints = [
    iam_mw.EndpointComparator("/"),
    iam_mw.EndpointComparator("/v1/"),
    iam_mw.EndpointComparator("/v1/health/"),
    iam_mw.EndpointComparator("/v1/iam/"),
    iam_mw.EndpointComparator("/v1/iam/users/", methods=[ra_c.POST]),
    iam_mw.EndpointComparator(
        f"/v1/iam/users/({ra_types.UUID_RE_TEMPLATE})"
        "/actions/reset_password/invoke",
        methods=[ra_c.POST],
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/clients/({ra_types.UUID_RE_TEMPLATE})",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/clients/({ra_types.UUID_RE_TEMPLATE})"
        "/actions/get_token/invoke",
        methods=[ra_c.POST],
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/clients/({ra_types.UUID_RE_TEMPLATE})"
        "/actions/reset_password/invoke",
        methods=[ra_c.POST],
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/clients/({ra_types.UUID_RE_TEMPLATE})/actions/jwks",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/users/({ra_types.UUID_RE_TEMPLATE})"
        "/actions/confirm_email/invoke",
        methods=[ra_c.POST],
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/idp/({ra_types.UUID_RE_TEMPLATE})",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/idp/({ra_types.UUID_RE_TEMPLATE})/.well-known/",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/idp/({ra_types.UUID_RE_TEMPLATE})"
        "/.well-known/openid-configuration",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/idp/({ra_types.UUID_RE_TEMPLATE})"
        "/actions/authorize/invoke",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/idp/({ra_types.UUID_RE_TEMPLATE})/actions/login/invoke",
    ),
    iam_mw.EndpointComparator(
        f"/v1/iam/authorization_requests/({ra_types.UUID_RE_TEMPLATE})",
    ),
]


class UserApiApp(routes.RootRoute):
    pass


# Route to /v1/ endpoint.
setattr(
    UserApiApp,
    versions.API_VERSION_v1,
    routes.route(app_routes.ApiEndpointRoute),
)


def get_api_application():
    return UserApiApp


def get_openapi_engine():
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(
            title=f"Genesis Core {versions.API_VERSION_v1} User API",
            version=version.version_info.release_string(),
            description=f"OpenAPI - Genesis Core {versions.API_VERSION_v1}",
        ),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
    )
    return openapi_engine


def build_wsgi_application(context_storage, token_algorithm):
    return middlewares.attach_middlewares(
        applications.OpenApiApplication(
            route_class=get_api_application(),
            openapi_engine=get_openapi_engine(),
        ),
        [
            middlewares.configure_middleware(
                iam_mw.GenesisCoreAuthMiddleware,
                # service_name="iam",
                token_algorithm=token_algorithm,
                context_kwargs={
                    "context_storage": context_storage,
                },
                iam_engine_driver=drivers.DirectDriver(),
                skip_auth_endpoints=skip_auth_endpoints,
            ),
            errors_mw.ErrorsHandlerMiddleware,
            logging_mw.LoggingMiddleware,
        ],
    )
