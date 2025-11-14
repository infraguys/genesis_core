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
import typing as tp

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


log = logging.getLogger(__name__)


class FirebaseAppCheckVerifier(AbstractVerifier):
    """
    Firebase App Check verifier.

    Verifies Firebase App Check tokens from mobile clients.
    """

    FIREBASE_HEADERS = [
        "X-Firebase-AppCheck",
        "X-Goog-Firebase-AppCheck",
    ]

    def __init__(self, config: tp.Dict[str, tp.Any] = None):
        """
        Initialize FirebaseAppCheckVerifier.

        :param config: Configuration dictionary with:
            - credentials_path: Path to Firebase service account JSON file
            - project_id: Firebase project ID (optional, can be in credentials)
            - allowed_app_ids: List of allowed app IDs (optional)
            - mode: "enforce" or "report-only" (default: "enforce")
        """
        self.config = config or {}
        self._app = None
        self._initialized = False

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK if not already initialized."""
        if self._initialized:
            return

        if firebase_admin is None:
            raise RuntimeError(
                "firebase-admin package is not installed. "
                "Install it with: pip install firebase-admin"
            )

        # Check if Firebase app is already initialized
        try:
            firebase_admin.get_app()
            self._initialized = True
            return
        except ValueError:
            # App not initialized, continue
            pass

        # Initialize with credentials
        credentials_path = self.config.get("credentials_path")
        if not credentials_path:
            raise ValueError(
                "Firebase credentials_path is required in config"
            )

        if not os.path.exists(credentials_path):
            raise ValueError(
                f"Firebase credentials file not found: {credentials_path}"
            )

        cred = credentials.Certificate(credentials_path)
        self._app = firebase_admin.initialize_app(cred)
        self._initialized = True
        log.info("Firebase Admin SDK initialized")

    def _get_token_from_request(self, request) -> tp.Optional[str]:
        """
        Extract Firebase App Check token from request headers.

        :param request: The request object
        :return: Token string or None if not found
        """
        for header_name in self.FIREBASE_HEADERS:
            token = request.headers.get(header_name)
            if token:
                return token
        return None

    def verify(self, request) -> tp.Tuple[bool, tp.Optional[str]]:
        """
        Verify Firebase App Check token.

        :param request: The request object
        :return: Tuple of (ok: bool, reason: str | None)
        """
        try:
            self._initialize_firebase()
        except Exception as e:
            log.error(f"Failed to initialize Firebase: {e}")
            return False, f"Firebase initialization error: {str(e)}"

        token = self._get_token_from_request(request)
        if not token:
            return False, "Firebase App Check token not found in request headers"

        try:
            # Verify the token
            app_check_token = app_check.verify_token(token)

            # Check allowed app IDs if configured
            allowed_app_ids = self.config.get("allowed_app_ids")
            if allowed_app_ids:
                app_id = app_check_token.get("app_id")
                if app_id not in allowed_app_ids:
                    log.warning(
                        f"Firebase App Check: app_id {app_id} not in allowed list"
                    )
                    return False, f"App ID {app_id} is not allowed"

            log.debug(
                f"Firebase App Check verified successfully: "
                f"app_id={app_check_token.get('app_id')}"
            )
            return True, None

        except firebase_exceptions.InvalidArgumentError as e:
            log.warning(f"Firebase App Check invalid argument: {e}")
            return False, f"Invalid Firebase App Check token: {str(e)}"
        except firebase_exceptions.PermissionDeniedError as e:
            log.warning(f"Firebase App Check permission denied: {e}")
            return False, f"Firebase App Check permission denied: {str(e)}"
        except Exception as e:
            log.error(f"Firebase App Check verification error: {e}")
            return False, f"Firebase App Check verification failed: {str(e)}"

