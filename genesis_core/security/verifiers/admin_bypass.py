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

import logging
from typing import Any

from restalchemy.common import contexts
from restalchemy.common import exceptions as ra_e
from restalchemy.dm import filters as ra_filters
from restalchemy.dm import types as ra_types

from genesis_core.user_api.iam import constants as iam_c
from genesis_core.user_api.iam.dm import models
from genesis_core.user_api.iam import exceptions as iam_exceptions
from gcl_iam import exceptions as iam_e
from gcl_iam import tokens
from genesis_core.security.interfaces import AbstractVerifier


log = logging.getLogger(__name__)


class AdminBypassVerifier(AbstractVerifier):
    """Allows admin/bypass users to skip validation.

    Rule format (IamClient.rules):
      {"kind": "admin_bypass", "bypass_users": ["admin@example.com", "<uuid>", ...]}
    """

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    @classmethod
    def get_rule_scheme(cls) -> dict[str, Any]:
        return {
            "kind": ra_types.String(max_length=64),
            "bypass_users": ra_types.List(),
        }

    def can_handle(self, request) -> bool:
        return request.headers.get("Authorization", "").startswith("Bearer ")

    def verify(self, request) -> None:
        ctx = contexts.get_context()
        token_algorithm = ctx.context_storage.get(
            iam_c.STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM
        )
        if not token_algorithm:
            raise iam_exceptions.CanNotCreateUser(message="Token algorithm is not configured")

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise iam_exceptions.CanNotCreateUser(message="Authorization header is not a Bearer token")

        try:
            auth_token = tokens.AuthToken(
                token=auth_header[7:].strip(),
                algorithm=token_algorithm,
                ignore_audience=True,
            )
            token = models.Token.objects.get_one(
                filters={"uuid": ra_filters.EQ(auth_token.uuid)},
            )
            token.validate_expiration()
            user = token.user
        except iam_e.InvalidAuthTokenError as e:
            log.debug("Admin bypass verification failed: token expired or invalid: %s", e)
            raise iam_exceptions.CanNotCreateUser(message="Token expired or invalid")
        except (ra_e.NotFoundError, ValueError, TypeError, KeyError) as e:
            log.debug("Admin bypass verification failed during token processing: %s", e)
            raise iam_exceptions.CanNotCreateUser(message="Admin bypass verification failed")

        if any(role.name.lower() == "admin" for role in user.get_my_roles().get_roles()):
            return

        bypass_users = self.config.get("bypass_users", [])
        bypass_list = {str(u).lower() for u in bypass_users}
        if (user.email and user.email.lower() in bypass_list) or str(user.uuid).lower() in bypass_list:
            return

        raise iam_exceptions.CanNotCreateUser(message="User is not allowed to bypass validation")


