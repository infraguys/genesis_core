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

from gcl_iam import tokens
from genesis_core.user_api.iam.dm import models as iam_models
from restalchemy.dm import filters as ra_filters


log = logging.getLogger(__name__)

FIREBASE_HEADERS = [
    "X-Firebase-AppCheck",
    "X-Goog-Firebase-AppCheck",
]


class SecurityPolicy:
    def __init__(self, registry, token_algorithm=None):
        self.registry = registry
        self.token_algorithm = token_algorithm

    def _has_admin_token(self, request) -> bool:
        if not self.token_algorithm:
            return False

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        try:
            auth_token = tokens.AuthToken(
                token=auth_header[7:].strip(),
                algorithm=self.token_algorithm,
                ignore_audience=True,
            )
            token = iam_models.Token.objects.get_one(
                filters={"uuid": ra_filters.EQ(auth_token.uuid)},
            )
            token.validate_expiration()
            roles = token.user.get_my_roles()
            return any(role.name.lower() == "admin" for role in roles._roles)
        except Exception:
            log.exception("Admin token check failed")
            return False

    def _has_firebase_app_check(self, request) -> bool:
        return any(request.headers.get(h) for h in FIREBASE_HEADERS)

    def get_required_verifiers(
        self, request
    ) -> tuple[bool, list[str]]:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            if self._has_admin_token(request):
                log.debug("admin token detected – bypass verification")
                return True, []
            log.debug("Authorization Bearer present but not admin token – reject")
            return False, []

        if self._has_firebase_app_check(request):
            log.debug("Firebase App Check detected – using firebase_app_check verifier")
            return False, ["firebase_app_check"]

        log.debug("No Firebase headers – using captcha verifier")
        return False, ["captcha"]

