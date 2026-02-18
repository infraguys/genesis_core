# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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

import bazooka


class IdpClient:
    def __init__(self, endpoint, timeout=5):
        super().__init__()
        self._endpoint = endpoint
        self._client = bazooka.Client(default_timeout=timeout)

    def get_idp_metadata(self):
        return self._client.get(self._endpoint).json()

    def get_user_info(self, token):
        return self._client.get(
            self.get_idp_metadata()["userinfo_endpoint"],
            headers={
                "Authorization": f"Bearer {token}",
            },
        ).json()
