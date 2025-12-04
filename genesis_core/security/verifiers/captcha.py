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
import logging

from genesis_core.security.interfaces import AbstractVerifier


log = logging.getLogger(__name__)


class CaptchaVerifier(AbstractVerifier):
    """Simple CAPTCHA verifier.

    Expected request:
      - Header 'X-Captcha' must be present.

    Config (rule/global) options:
      - mode: "enforce" | "report-only" (not used here directly, but kept
        for a common contract with other verifiers).
    """

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def can_handle(self, request) -> bool:
        """Check if request has X-Captcha header."""
        return bool(request.headers.get("X-Captcha"))

    def verify(self, request) -> tuple[bool, str | None]:
        token = request.headers.get("X-Captcha")
        if not token:
            log.warning("CAPTCHA token not found in headers")
            return False, "CAPTCHA token not found"

        # Here we could call a real CAPTCHA provider. For now we only check
        # that the header is present and non-empty.
        return True, None

