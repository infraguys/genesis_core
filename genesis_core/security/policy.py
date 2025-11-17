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

from gcl_iam import tokens


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

    def __init__(self, registry, token_algorithm=None):
        """
        Initialize SecurityPolicy.

        :param registry: VerifierRegistry instance
        :param token_algorithm: Token algorithm for validating tokens (optional)
        """
        self.registry = registry
        self.token_algorithm = token_algorithm

    def _has_admin_token(self, request) -> bool:
        """
        Check if request has valid admin IAM token.

        Since /v1/iam/users/ POST is always skip_auth_endpoint,
        IAM context is never set. We validate token directly from DB.

        :param request: The request object
        :return: True if admin token is present and valid
        """
        if not self.token_algorithm:
            log.warning("Token algorithm not set, cannot validate admin token")
            return False

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token_string = auth_header[7:].strip()

        try:
            # Decode token - this will raise exception if token is invalid
            # ignore_audience=True to allow tokens from any client
            auth_token = tokens.AuthToken(
                token=token_string,
                algorithm=self.token_algorithm,
                ignore_audience=True,
            )
            token_uuid = auth_token.uuid

            # Check if token exists in database and is valid
            from genesis_core.user_api.iam.dm import models as iam_models
            from restalchemy.dm import filters as ra_filters

            # CRITICAL: Token must exist in DB, otherwise it's fake
            for token in iam_models.Token.objects.get_all(
                filters={"uuid": ra_filters.EQ(token_uuid)},
                limit=1,
            ):
                token.validate_expiration()
                log.info(f"Valid admin token detected: {token_uuid}")
                return True

            # Token decoded but not found in DB = fake token
            log.warning(f"Token decoded but not found in database: {token_uuid}")
            return False

        except Exception as e:
            # Token decode failed or validation failed = invalid token
            log.warning(f"Token validation failed: {type(e).__name__}: {e}")
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
        # If Authorization header is present but token is invalid, reject immediately
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Token header present - must be valid admin token
            if self._has_admin_token(request):
                log.debug("Admin token detected, bypassing verification")
                return True, []
            else:
                # Invalid token with Authorization header - reject
                log.warning("Authorization header present but token is invalid")
                return False, []  # Empty verifiers = reject

        # Check for Firebase App Check token
        if self._has_firebase_app_check(request):
            log.debug("Firebase App Check token detected")
            return False, ["firebase_app_check"]

        # Default: require CAPTCHA for web clients (no Authorization header)
        log.debug("No Firebase token, requiring CAPTCHA")
        return False, ["captcha"]

