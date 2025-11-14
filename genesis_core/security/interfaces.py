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

import abc
import typing as tp


class AbstractVerifier(abc.ABC):
    """Base interface for request verifiers."""

    @abc.abstractmethod
    def verify(self, request) -> tp.Tuple[bool, tp.Optional[str]]:
        """
        Verify the request.

        :param request: The request object
        :return: Tuple of (ok: bool, reason: str | None)
            - ok: True if verification passed, False otherwise
            - reason: Error message if verification failed, None if passed
        """
        pass

