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
import os
from typing import Any

try:
    import firebase_admin
    from firebase_admin import app_check
    from firebase_admin import credentials
    from firebase_admin import exceptions as firebase_exceptions
except ImportError:
    firebase_admin = None
    app_check = None
    credentials = None
    firebase_exceptions = None

from genesis_core.security.interfaces import AbstractVerifier
from genesis_core.user_api.iam import exceptions as iam_exceptions


log = logging.getLogger(__name__)


class FirebaseAppCheckVerifier(AbstractVerifier):
    """Firebase App Check verifier.

    Rule format (IamClient.rules):
      {
        "kind": "firebase_app_check",
        "credentials_path": "/path/to/firebase-credentials.json",
        "allowed_app_ids": ["app-id-1", "app-id-2", ...],
        "mode": "enforce"
      }
    """

    FIREBASE_HEADERS = [
        "X-Firebase-AppCheck",
        "X-Goog-Firebase-AppCheck",
    ]

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self._app = None
        self._initialized = False

    def _initialize_firebase(self):
        if self._initialized:
            return

        if firebase_admin is None:
            raise RuntimeError("firebase-admin package is not installed")

        try:
            self._app = firebase_admin.get_app()
            self._initialized = True
            return
        except ValueError:
            pass

        credentials_path = self.config.get("credentials_path")
        if not credentials_path:
            raise ValueError("Firebase credentials_path is required in config")

        if not os.path.exists(credentials_path):
            raise ValueError(f"Firebase credentials file not found: {credentials_path}")

        cred = credentials.Certificate(credentials_path)
        self._app = firebase_admin.initialize_app(cred)
        self._initialized = True

    def can_handle(self, request) -> bool:
        return any(request.headers.get(h) for h in self.FIREBASE_HEADERS)

    def _get_token_from_request(self, request) -> str | None:
        for header_name in self.FIREBASE_HEADERS:
            token = request.headers.get(header_name)
            if token:
                return token
        return None

    def verify(self, request) -> None:
        self._initialize_firebase()
        token = self._get_token_from_request(request)
        if not token:
            raise iam_exceptions.CanNotCreateUser(message="Firebase App Check token not found")

        try:
            app_check_token = app_check.verify_token(token, app=self._app)
            allowed_app_ids = self.config.get("allowed_app_ids")
            if allowed_app_ids:
                app_id = app_check_token.get("app_id")
                if app_id not in allowed_app_ids:
                    raise iam_exceptions.CanNotCreateUser(message=f"App ID {app_id} is not allowed")
        except iam_exceptions.CanNotCreateUser:
            raise
        except firebase_exceptions.InvalidArgumentError as e:
            raise iam_exceptions.CanNotCreateUser(message=f"Invalid Firebase App Check token: {str(e)}")
        except firebase_exceptions.PermissionDeniedError as e:
            raise iam_exceptions.CanNotCreateUser(message=f"Firebase App Check permission denied: {str(e)}")
        except Exception as e:
            raise iam_exceptions.CanNotCreateUser(message=f"Firebase App Check verification failed: {str(e)}")

