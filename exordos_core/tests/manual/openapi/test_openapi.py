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

"""The published documents have to be the ones the services serve.

These files used to be written here, by asking four running services for
their document and committing the answer. They are built from the route
tree instead now (`exordos_core.common.openapi`), which is what lets the
site be built without a database -- honest only as long as building one
without a service gives what a service gives. That is what this checks, and
it is the one place the substitutions made for the offline build are held
against the real thing.

Run against a live stand: `tox -e openapi_spec`.
"""

from gcl_iam.tests.functional import clients as iam_clients
from gcl_sdk.agents.universal.api.packers import EXORDOS_NODE_UUID_HEADER

from exordos_core.common import openapi

SPECIFICATIONS_PATH = "specifications/3.0.3"

# What an agent has to say to be answered at all.
AGENT_HEADERS = {
    "Content-Type": "application/x-genesis-agent-chacha20-poly1305-encrypted",
}


def assert_served_matches_built(api, response):
    """Compare a served document with the one built without a service."""
    assert response.status_code == 200

    served = response.json()
    # Both parts are the request's, not the API's: the served document
    # names the host it was asked on and the release serving it.
    served["servers"][0]["url"] = api.url
    served["info"]["version"] = openapi.PUBLISHED_VERSION

    assert served == openapi.build(api)


class TestGetOpenApiSpecs:
    def test_user_openapi(
        self,
        user_api,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)

        response = client.get(
            f"{user_api.get_endpoint()}{SPECIFICATIONS_PATH}", timeout=30
        )

        assert_served_matches_built(openapi.USER_API, response)

    def test_boot_openapi(
        self,
        boot_api_service,
        boot_api_noauth_client: iam_clients.GenesisCoreTestNoAuthRESTClient,
    ):
        response = boot_api_noauth_client.get(
            f"{boot_api_service.get_endpoint()}{SPECIFICATIONS_PATH}"
        )

        assert_served_matches_built(openapi.BOOT_API, response)

    def test_orch_openapi(
        self,
        orch_api_service,
        orch_api_noauth_client: iam_clients.GenesisCoreTestNoAuthRESTClient,
        default_node,
    ):
        response = orch_api_noauth_client.get(
            f"{orch_api_service.get_endpoint()}{SPECIFICATIONS_PATH}",
            headers={
                EXORDOS_NODE_UUID_HEADER: default_node["uuid"],
                **AGENT_HEADERS,
            },
        )

        assert_served_matches_built(openapi.ORCH_API, response)

    def test_status_openapi(
        self,
        status_api_service,
        status_api_noauth_client: iam_clients.GenesisCoreTestNoAuthRESTClient,
        default_node,
    ):
        response = status_api_noauth_client.get(
            f"{status_api_service.get_endpoint()}{SPECIFICATIONS_PATH}",
            headers={
                EXORDOS_NODE_UUID_HEADER: default_node["uuid"],
                **AGENT_HEADERS,
            },
        )

        assert_served_matches_built(openapi.STATUS_API, response)
