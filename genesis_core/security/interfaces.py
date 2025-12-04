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


class AbstractVerifier(abc.ABC):
    @abc.abstractmethod
    def can_handle(self, request) -> bool:
        """Check if this verifier can handle the given request.
        
        This method should check if the request has the necessary headers/tokens
        for this verifier type. It should NOT perform actual validation,
        only determine if this verifier is applicable to the request.
        
        Returns:
            True if this verifier can handle the request, False otherwise.
        """
        pass

    @abc.abstractmethod
    def verify(self, request) -> tuple[bool, str | None]:
        """Perform actual validation of the request.
        
        This method is only called if can_handle() returned True.
        It should perform the actual validation logic.
        
        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        pass

