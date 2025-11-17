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

from restalchemy.api import constants as ra_c
from restalchemy.api.middlewares import Middleware

from genesis_core.common import exceptions as common_exc
from genesis_core.security.policy import SecurityPolicy
from genesis_core.security.registry import VerifierRegistry


log = logging.getLogger(__name__)


class RequestVerificationMiddleware(Middleware):
    VERIFICATION_ENDPOINTS = [
        ("/v1/iam/users/", [ra_c.POST]),
    ]

    def __init__(self, application, registry: VerifierRegistry = None, policy=None):
        super().__init__(application)
        self.registry = registry or VerifierRegistry()
        self.policy = policy or SecurityPolicy(self.registry)

    def _should_verify(self, path: str, method: str) -> bool:
        return any(
            path.startswith(endpoint_path) and method in methods
            for endpoint_path, methods in self.VERIFICATION_ENDPOINTS
        )

    def process_request(self, req):
        if not self._should_verify(req.path, req.method):
            return None

        bypass, verifier_names = self.policy.get_required_verifiers(
            req, req.path, req.method
        )

        if bypass:
            return None

        if not verifier_names:
            raise common_exc.CommonForbiddenException()

        for verifier_name in verifier_names:
            verifier = self.registry.get(verifier_name)
            if not verifier:
                continue
            ok, _ = verifier.verify(req)
            if not ok:
                raise common_exc.CommonForbiddenException()

        return None

