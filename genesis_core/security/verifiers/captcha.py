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

import typing as tp

from genesis_core.security.interfaces import AbstractVerifier


class CaptchaVerifier(AbstractVerifier):
    """
    Captcha verifier stub.

    This is a placeholder implementation that always returns success.
    In the future, this should be replaced with actual CAPTCHA verification.
    """

    def __init__(self, config: tp.Dict[str, tp.Any] = None):
        """
        Initialize CaptchaVerifier.

        :param config: Configuration dictionary (currently unused)
        """
        self.config = config or {}

    def verify(self, request) -> tp.Tuple[bool, tp.Optional[str]]:
        """
        Verify CAPTCHA (stub implementation).

        :param request: The request object
        :return: (True, None) - always succeeds
        """
        # TODO: Implement actual CAPTCHA verification
        return True, None

