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
import webob


class AbstractVerifier(abc.ABC):
    @abc.abstractmethod
    def can_handle(self, request: webob.Request) -> bool:
        """Check if this verifier can handle the request."""

    @abc.abstractmethod
    def verify(self, request: webob.Request) -> None:
        """Perform validation. Raises exception on failure, returns None on success. Called only if can_handle() returned True."""

