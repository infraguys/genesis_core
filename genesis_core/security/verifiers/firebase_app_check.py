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

from genesis_core.security.interfaces import AbstractVerifier
from genesis_core.user_api.iam import exceptions as iam_exceptions

try:
    import firebase_admin
    from firebase_admin import app_check, credentials
    from firebase_admin import exceptions as firebase_exceptions
except ImportError:
    firebase_admin = None
    app_check = None
    credentials = None
    firebase_exceptions = None


log = logging.getLogger(__name__)


class FirebaseAppCheckVerifier(AbstractVerifier):
    """Firebase App Check verifier.

    Rule format (IamClient.rules):
      {
        "kind": "firebase_app_check",
        "credentials_path": "/path/to/firebase-credentials.json",
        "allowed_app_ids": ["app-id-1", "app-id-2", ...],
      }
    """

    FIREBASE_HEADERS = [
        "X-Firebase-AppCheck",
        "X-Goog-Firebase-AppCheck",
    ]

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        raw_allowed = self.config.get("allowed_app_ids") or []
        self._allowed_app_ids = {str(app_id) for app_id in raw_allowed}

    def _get_firebase_app(self):
        if firebase_admin is None:
            raise RuntimeError("firebase-admin package is not installed")

        try:
            return firebase_admin.get_app()
        except ValueError:
            # No default app initialized yet – initialize it from credentials_path
            credentials_path = self.config.get("credentials_path")
            if not credentials_path:
                raise ValueError("Firebase credentials_path is required in config")

            cred = credentials.Certificate(credentials_path)
            # Return the initialized default app directly
            return firebase_admin.initialize_app(cred)

    def can_handle(self, request) -> bool:
        return any(request.headers.get(h) for h in self.FIREBASE_HEADERS)

    def _get_token_from_request(self, request) -> str | None:
        for header_name in self.FIREBASE_HEADERS:
            token = request.headers.get(header_name)
            if token:
                return token
        return None

    def verify(self, request) -> None:
        app = self._get_firebase_app()
        token = self._get_token_from_request(request)
        if not token:
            raise iam_exceptions.FirebaseAppCheckValidationFailed(
                message="Firebase App Check token not found."
            )

        try:
            app_check_token = app_check.verify_token(token, app=app)
        except firebase_exceptions.InvalidArgumentError as e:
            raise iam_exceptions.FirebaseAppCheckValidationFailed(
                message="Invalid App Check token."
            ) from e
        except firebase_exceptions.PermissionDeniedError as e:
            raise iam_exceptions.FirebaseAppCheckValidationFailed(
                message="App Check verification failed: permission denied."
            ) from e
        except firebase_exceptions.FirebaseError as e:
            log.error("Unexpected Firebase App Check error: %s", e)
            raise iam_exceptions.FirebaseAppCheckValidationFailed(
                message="App Check verification failed due to a system error."
            ) from e

        # Fail fast for not-allowed app IDs once token is verified
        if self._allowed_app_ids:
            app_id = app_check_token.get("app_id")
            if app_id not in self._allowed_app_ids:
                raise iam_exceptions.FirebaseAppCheckValidationFailed(
                    message=f"App ID {app_id} is not allowed."
                )

