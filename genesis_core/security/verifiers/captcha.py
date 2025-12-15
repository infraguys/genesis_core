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

import json
import logging
from typing import Any

import altcha
from restalchemy.dm import types as ra_types

from genesis_core.security.interfaces import AbstractVerifier
from genesis_core.user_api.iam import exceptions as iam_exceptions


log = logging.getLogger(__name__)


class CaptchaVerifier(AbstractVerifier):
    """CAPTCHA verifier using altcha. Requires X-Captcha header.

    Rule format (IamClient.rules):
      {
        "kind": "captcha",
        "hmac_key": "your-hmac-key-here",
        "mode": "enforce"
      }
    """

    CAPTCHA_HEADER = "X-Captcha"

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    @classmethod
    def get_rule_scheme(cls) -> dict[str, ra_types.BaseType]:
        return {
            "kind": ra_types.String(max_length=64),
            "hmac_key": ra_types.String(),
            "mode": ra_types.Enum(["enforce", "report-only"]),
        }

    def can_handle(self, request) -> bool:
        return bool(request.headers.get(self.CAPTCHA_HEADER))

    def _get_payload_from_request(self, request) -> dict | None:
        """Extract and parse CAPTCHA payload from request header."""
        captcha_header = request.headers.get(self.CAPTCHA_HEADER)
        try:
            return json.loads(captcha_header)
        except (json.JSONDecodeError, TypeError) as e:
            log.debug("Failed to parse CAPTCHA payload: %s", e)
            return None

    def verify(self, request) -> None:
        payload = self._get_payload_from_request(request)
        if not payload:
            raise iam_exceptions.CanNotCreateUser(message="Invalid CAPTCHA payload")

        hmac_key = self.config.get("hmac_key")
        if not hmac_key:
            raise iam_exceptions.CanNotCreateUser(message="CAPTCHA hmac_key not configured in rule")

        try:
            verified, error = altcha.verify_solution(
                payload,
                hmac_key=hmac_key,
                check_expires=True,
            )
        except (ValueError, TypeError, KeyError) as e:
            log.debug("CAPTCHA verification failed: %s", e)
            raise iam_exceptions.CanNotCreateUser(message="CAPTCHA verification failed.")
        
        if not verified:
            raise iam_exceptions.CanNotCreateUser(message=error or "CAPTCHA verification failed")

