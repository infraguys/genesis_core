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

from typing import Any

import jwt.exceptions
from restalchemy.dm import filters as ra_filters
import webob

from genesis_core.user_api.iam.dm import models
from genesis_core.user_api.iam import exceptions as iam_exceptions
from gcl_iam import tokens
from genesis_core.security.base import AbstractVerifier
from genesis_core.user_api.iam import drivers as iam_drivers


class AdminBypassVerifier(AbstractVerifier):
    """Allows admin/bypass users to skip validation.

    Rule format (IamClient.rules):
      {"kind": "admin_bypass", "bypass_users": ["admin@example.com", "<uuid>", ...]}
    """

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def can_handle(self, request: webob.Request) -> bool:
        return request.headers.get("Authorization", "").startswith("Bearer ")

    def verify(self, request: webob.Request) -> None:
        auth = request.headers.get("Authorization", "")
        raw = auth[7:].strip()
        try:
            unverified_token = tokens.UnverifiedToken(raw)
        except jwt.exceptions.DecodeError as e:
            raise iam_exceptions.AdminBypassValidationFailed() from e
        algorithm = iam_drivers.DirectDriver().get_algorithm(unverified_token)
        auth_token = tokens.AuthToken(
            token=raw,
            algorithm=algorithm,
            ignore_audience=True,
        )
        token = models.Token.objects.get_one(
            filters={"uuid": ra_filters.EQ(auth_token.uuid)},
        )
        token.validate_expiration()
        user = token.user

        bypass_users = self.config.get("bypass_users", [])
        bypass_list = {str(u).lower() for u in bypass_users}
        if (user.email and user.email.lower() in bypass_list) or str(user.uuid).lower() in bypass_list:
            return

        raise iam_exceptions.AdminBypassValidationFailed()


