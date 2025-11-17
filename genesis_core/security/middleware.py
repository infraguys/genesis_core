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
    """
    Middleware for request verification.

    Applies security verifiers (CAPTCHA, Firebase App Check, etc.)
    based on the request characteristics and policy.
    """

    # Endpoints that require verification
    VERIFICATION_ENDPOINTS = [
        ("/v1/iam/users/", [ra_c.POST]),
    ]

    def __init__(self, application, registry: VerifierRegistry = None, policy=None):
        """
        Initialize RequestVerificationMiddleware.

        :param application: WSGI application
        :param registry: VerifierRegistry instance (optional, will create if not provided)
        :param policy: SecurityPolicy instance (optional, will create if not provided)
        """
        super().__init__(application)
        self.registry = registry or VerifierRegistry()
        self.policy = policy or SecurityPolicy(self.registry)

    def _should_verify(self, path: str, method: str) -> bool:
        """
        Check if endpoint requires verification.

        :param path: Request path
        :param method: HTTP method
        :return: True if verification is required
        """
        for endpoint_path, methods in self.VERIFICATION_ENDPOINTS:
            if path.startswith(endpoint_path) and method in methods:
                return True
        return False

    def process_request(self, req):
        """
        Process request before it reaches the controller.

        :param req: Request object
        :return: Response if verification failed, None to continue
        """
        path = req.path
        method = req.method

        # Check if this endpoint requires verification
        if not self._should_verify(path, method):
            log.debug(f"RequestVerificationMiddleware: endpoint {method} {path} does not require verification")
            return None
        
        log.info(f"RequestVerificationMiddleware: processing {method} {path}")
        log.debug(f"RequestVerificationMiddleware: headers: Authorization={bool(req.headers.get('Authorization'))}")

        # Determine which verifiers are needed
        bypass, verifier_names = self.policy.get_required_verifiers(
            req, path, method
        )

        if bypass:
            log.info(f"Bypassing verification for {method} {path} (admin token detected)")
            return None

        if not verifier_names:
            log.warning(f"Request rejected: no verifiers and bypass=False for {method} {path}")
            raise common_exc.CommonForbiddenException()

        # Run required verifiers
        for verifier_name in verifier_names:
            verifier = self.registry.get(verifier_name)
            if not verifier:
                log.warning(
                    f"Verifier '{verifier_name}' not found, "
                    f"skipping verification"
                )
                continue

            log.debug(
                f"Running verifier '{verifier_name}' for {method} {path}"
            )
            ok, reason = verifier.verify(req)

            if not ok:
                log.warning(
                    f"Verification failed for {method} {path}: "
                    f"verifier={verifier_name}, reason={reason}"
                )
                raise common_exc.CommonForbiddenException()

        # All verifications passed
        log.debug(f"Verification passed for {method} {path}")
        return None

