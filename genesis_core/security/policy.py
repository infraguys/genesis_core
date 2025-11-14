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
import typing as tp

from restalchemy.common import contexts


log = logging.getLogger(__name__)

# Firebase App Check header names
FIREBASE_HEADERS = [
    "X-Firebase-AppCheck",
    "X-Goog-Firebase-AppCheck",
]


class SecurityPolicy:
    """
    Security policy evaluator.

    Determines which verifiers should be applied to a request based on
    the request characteristics (admin token, Firebase token, etc.).
    """

    def __init__(self, registry):
        """
        Initialize SecurityPolicy.

        :param registry: VerifierRegistry instance
        """
        self.registry = registry

    def _has_admin_token(self, request) -> bool:
        """
        Check if request has valid admin IAM token.

        :param request: The request object
        :return: True if admin token is present and valid
        """
        try:
            # Check if Authorization header is present
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return False

            # Try to get IAM context
            # Note: For endpoints in skip_auth_endpoints, the auth middleware
            # may still validate the token if it's provided, but may not set
            # iam_context. We check both cases.
            try:
                ctx = contexts.get_context()
                if hasattr(ctx, "iam_context"):
                    iam_context = ctx.iam_context
                    if hasattr(iam_context, "token_info"):
                        token_info = iam_context.token_info
                        if token_info and hasattr(token_info, "uuid"):
                            # Token is present and valid in context
                            log.debug("Valid admin token detected in request (from context)")
                            return True
            except Exception:
                # Context may not be available for skip_auth_endpoints
                pass

            # If we have Authorization header with Bearer token, and the request
            # reached this middleware (meaning it wasn't rejected by auth middleware),
            # we consider it a valid admin token for service-to-service calls.
            # The auth middleware would have rejected invalid tokens.
            log.debug("Admin token detected in Authorization header")
            return True

        except Exception as e:
            log.debug(f"Error checking admin token: {e}")
            return False

    def _has_firebase_app_check(self, request) -> bool:
        """
        Check if request has Firebase App Check token.

        :param request: The request object
        :return: True if Firebase token is present
        """
        for header_name in FIREBASE_HEADERS:
            if request.headers.get(header_name):
                return True
        return False

    def get_required_verifiers(
        self, request, path: str, method: str
    ) -> tp.Tuple[bool, tp.List[str]]:
        """
        Determine which verifiers are required for the request.

        :param request: The request object
        :param path: Request path
        :param method: HTTP method
        :return: Tuple of (bypass: bool, verifiers: List[str])
            - bypass: True if no verification is needed (admin token)
            - verifiers: List of verifier names to run
        """
        # Check for admin token first
        if self._has_admin_token(request):
            log.debug("Admin token detected, bypassing verification")
            return True, []

        # Check for Firebase App Check token
        if self._has_firebase_app_check(request):
            log.debug("Firebase App Check token detected")
            return False, ["firebase_app_check"]

        # Default: require CAPTCHA for web clients
        log.debug("No Firebase token, requiring CAPTCHA")
        return False, ["captcha"]

