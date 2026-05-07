#    Copyright 2026 Genesis Corporation.
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

from gcl_iam import contexts as iam_contexts
import netaddr
from restalchemy.api import packers

from exordos_core.user_api.iam.dm import models

_RAW_PAYLOAD_MISSING = object()


class GenesisCoreAuthContext(iam_contexts.GenesisCoreAuthContext):
    """Custom auth context with security rules support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._raw_payload_cache = _RAW_PAYLOAD_MISSING

    def set_anonymous_bypass_matched(self) -> None:
        """Mark that AnonymousBypassVerifier Rule matched for this request.

        This is set by the AnonymousBypassVerifier when it successfully
        verifies an anonymous/unauthenticated request.
        """
        if not hasattr(self.request, "environ"):
            return
        self.request.environ["_anonymous_bypass_matched"] = True

    def is_anonymous_bypass_matched(self) -> bool:
        """Check if AnonymousBypassVerifier Rule matched for this request."""
        if not hasattr(self.request, "environ"):
            return False
        return self.request.environ.get("_anonymous_bypass_matched", False)

    def get_user_ip(self) -> tp.Optional[netaddr.IPAddress]:
        request = self.request
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return netaddr.IPAddress(forwarded_for.split(",")[0].strip())
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return netaddr.IPAddress(real_ip.strip())
        remote_addr = getattr(request, "remote_addr", None) or getattr(
            request, "client_addr", None
        )
        if remote_addr:
            return netaddr.IPAddress(str(remote_addr))
        environ = getattr(request, "environ", None)
        if environ:
            remote_env = environ.get("REMOTE_ADDR")
            return netaddr.IPAddress(remote_env) if remote_env else None
        return None

    def me(self):
        return models.User.me()

    def get_raw_payload(self) -> tp.Any:
        if self._raw_payload_cache is not _RAW_PAYLOAD_MISSING:
            return self._raw_payload_cache

        request = self.request
        content_type = packers.get_content_type(request.headers)
        packer_class = packers.get_packer(content_type)
        packer = packer_class(resource_type=None, request=request)
        payload = packer.unpack(value=request.body)

        self._raw_payload_cache = payload
        return payload
