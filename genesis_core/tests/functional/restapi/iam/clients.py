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

import bazooka
from bazooka import common

DEFAULT_ENDPOINT = "http://localhost:11010/"


class NoAuth:

    def build_headers(self, headers=None):
        return (headers or {}).copy()


class GenesisCoreAuth(NoAuth):

    def __init__(
        self,
        username: str,
        password: str,
        endpoint: str = DEFAULT_ENDPOINT,
        version: str = "v1",
        client_uuid: str = "00000000-0000-0000-0000-000000000000",
        client_id: str = "GenesisCoreClientId",
        client_secret: str = "GenesisCoreClientSecret",
        uuid: str = "00000000-0000-0000-0000-000000000000",
        email: str = "admin@genesis.com",
        project_id: str = None,
        timeout: int = 5,
    ):
        super().__init__()
        self._uuid = uuid
        self._email = email
        self._username = username
        self._password = password
        self._endpoint = common.force_last_slash(endpoint)
        self._version = version
        self._client_uuid = client_uuid
        self._client_id = client_id
        self._client_secret = client_secret
        self._project_id = project_id
        self._client = bazooka.Client(default_timeout=timeout)
        self._token_info = self._get_token_info()

    def _get_client_url(self):
        return (
            f"{common.force_last_slash(self._versioned_endpoint)}iam/clients/"
            f"{self._client_uuid}"
        )

    def _get_token_url(self):
        return f"{self._get_client_url()}/actions/get_token/invoke"

    def _get_me_url(self):
        return f"{self._get_client_url()}/actions/me"

    @property
    def _versioned_endpoint(self):
        return f"{self._endpoint}{common.force_last_slash(self._version)}"

    @property
    def uuid(self):
        return self._uuid

    @property
    def email(self):
        return self._email

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def client_uuid(self):
        return self._client_uuid

    @property
    def client_id(self):
        return self._client_id

    @property
    def client_secret(self):
        return self._client_secret

    @property
    def project_id(self):
        return self._project_id

    def _get_token_info(self):
        return self._client.post(
            self._get_token_url(),
            params=self._get_password_auth_params(),
        ).json()

    def build_headers(self, headers=None):
        token_info = self._token_info
        result = super().build_headers(headers=headers)
        result.update(
            {
                "Authorization": (
                    f"{token_info['token_type']} {token_info['access_token']}"
                ),
            }
        )
        return result

    def _get_password_auth_params(self):
        return {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": self._password,
            "scope": (
                f"project:{self._project_id}" if self._project_id else ""
            ),
        }


class SpecificationClient(common.RESTClientMixIn):

    def __init__(self, endpoint, timeout=5, spec_version="3.0.3", auth=None):
        super().__init__()
        self._endpoint = common.force_last_slash(endpoint)
        self._spec_version = spec_version
        self._client = bazooka.Client(default_timeout=timeout)
        self._auth = auth or NoAuth()

    def get_spec(self):
        return self._client.get(
            self._build_resource_uri(
                [
                    "specifications",
                    self._spec_version,
                ]
            ),
            headers=self._auth.build_headers(),
        ).json()


class BaseClient(common.RESTClientMixIn):

    def __init__(self, endpoint, spec, auth=None):
        super().__init__()
        self._endpoint = endpoint
        self._spec = spec
        self._auth = auth or NoAuth()

    def build_headers(self, headers=None):
        return self._auth.build_headers(headers=headers)


class NestedClient(BaseClient):

    def __init__(self, endpoint, spec, http_client, auth=None):
        super().__init__(endpoint=endpoint, spec=spec, auth=auth)
        self._client = http_client

    def filter_response(self, params=None, headers=None):
        return self._client.get(
            common.force_last_slash(self._endpoint),
            params=params,
            headers=self.build_headers(headers=headers),
        )

    def filter(self, params=None, headers=None):
        return self.filter_response(params=params, headers=headers).json()

    def create_response(self, body=None, params=None, headers=None):
        return self._client.post(
            common.force_last_slash(self._endpoint),
            json=body,
            params=params,
            headers=self.build_headers(headers=headers),
        )

    def create(self, body=None, params=None, headers=None):
        return self.create_response(
            body=body, params=params, headers=headers
        ).json()

    def get_response(self, resource_id, params=None, headers=None):
        return self._client.get(
            self._build_resource_uri([resource_id]),
            params=params,
            headers=self.build_headers(headers=headers),
        )

    def get(self, resource_id, params=None, headers=None):
        return self.get_response(
            resource_id, params=params, headers=headers
        ).json()

    def update_response(
        self, resource_id, body=None, params=None, headers=None
    ):
        return self._client.get(
            self._build_resource_uri([resource_id]),
            json=body,
            params=params,
            headers=self.build_headers(headers=headers),
        )

    def update(self, resource_id, body=None, params=None, headers=None):
        return self.get_response(
            resource_id, body=body, params=params, headers=headers
        ).json()

    def delete_response(self, resource_id, headers=None):
        return self._client.get(
            self._build_resource_uri([resource_id]),
            headers=self.build_headers(headers=headers),
        )

    def delete(self, resource_id, headers=None):
        self.get_response(resource_id, headers=headers)

    def __getattr__(self, name):
        return NestedClient(
            endpoint=self._build_collection_uri([self._endpoint, name]),
            spec=self._spec,
            http_client=self._client,
            auth=self._auth,
        )


class GenesisClient(BaseClient):

    def __init__(
        self, endpoint, version="v1", timeout=5, spec_client=None, auth=None
    ):
        self._spec_client = spec_client or SpecificationClient(
            endpoint=endpoint,
            timeout=timeout,
        )
        self._client = bazooka.Client(default_timeout=timeout)
        super().__init__(
            endpoint=endpoint,
            spec=self.fetch_spec(),
            auth=auth,
        )
        self._endpoint = endpoint
        self._version = version

    def _get_nested_client(self):
        return NestedClient(
            endpoint=(
                f"{self._endpoint}{common.force_last_slash(self._version)}"
            ),
            spec=self._spec,
            http_client=self._client,
            auth=self._auth,
        )

    def fetch_spec(self):
        return self._spec_client.get_spec()

    def __getattr__(self, name):
        return getattr(self._get_nested_client(), name)
