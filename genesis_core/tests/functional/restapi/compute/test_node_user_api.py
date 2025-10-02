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

import uuid as sys_uuid
import typing as tp

import pytest
from bazooka import exceptions as bazooka_exc
from gcl_iam.tests.functional import clients as iam_clients
from genesis_core.compute import constants as nc


class TestNodeUserApi:

    # Utils

    @staticmethod
    def _node_cmp_shallow(
        node_foo: tp.Dict[str, tp.Any],
        node_bar: tp.Dict[str, tp.Any],
    ):
        return all(
            (node_foo[key] == node_bar[key])
            for key in (
                "uuid",
                "name",
                "image",
                "cores",
                "ram",
                "status",
                "node_type",
            )
        )

    @staticmethod
    def _machine_cmp_shallow(
        machine_foo: tp.Dict[str, tp.Any],
        machine_bar: tp.Dict[str, tp.Any],
    ):
        return all(
            (machine_foo[key] == machine_bar[key])
            for key in (
                "uuid",
                "name",
                "cores",
                "ram",
                "status",
                "machine_type",
            )
        )

    # Common

    def test_version(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):

        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri([])

        response = client.get(url)
        assert response.status_code == 200

    # Nodes

    def test_nodes_list(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])

        response = client.get(url)

        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_nodes_add(
        self,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        node = node_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])

        response = client.post(url, json=node)
        output = response.json()

        assert response.status_code == 201
        assert self._node_cmp_shallow(node, output)

    def test_nodes_add_several(
        self,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        nodes = [node_factory(name=f"node{i}") for i in range(3)]
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])

        for node in nodes:
            response = client.post(url, json=node)
            output = response.json()
            assert response.status_code == 201
            assert self._node_cmp_shallow(node, output)

        response = client.get(url)
        output = response.json()
        assert len(output) == len(nodes)
        for node in nodes:
            assert any(self._node_cmp_shallow(node, item) for item in output)

    def test_nodes_update(
        self,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        node = node_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])

        response = client.post(url, json=node)
        output = response.json()
        assert response.status_code == 201

        update = {"cores": 2, "ram": 2048}
        url = client.build_resource_uri(["compute", "nodes", node["uuid"]])
        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["cores"] == 2
        assert output["ram"] == 2048

    def test_nodes_delete(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        node_factory: tp.Callable,
    ):
        node = node_factory()

        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])
        response = client.post(url, json=node)
        assert response.status_code == 201

        url = client.build_resource_uri(["compute", "nodes", node["uuid"]])
        response = client.delete(url)

        assert response.status_code == 204

        url = client.build_resource_uri(["compute", "nodes", node["uuid"]])
        with pytest.raises(bazooka_exc.NotFoundError):
            response = client.get(url)

    def test_nodes_default_volume(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        node_factory: tp.Callable,
    ):
        node = node_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "nodes"])

        response = client.post(url, json=node)
        output = response.json()

        assert response.status_code == 201
        assert output["root_disk_size"] == nc.DEF_ROOT_DISK_SIZE

    # Hypervisors

    def test_hyper_list_empty(
        self,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "hypervisors"])

        response = client.get(url)

        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_hyper_list(
        self,
        default_pool: tp.Dict[str, tp.Any],
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "hypervisors"])

        response = client.get(url)
        output = response.json()

        assert response.status_code == 200
        assert len(output) == 1
        assert output[0]["uuid"] == default_pool["uuid"]

    def test_hyper_add(
        self,
        pool_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        pool = pool_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "hypervisors"])

        response = client.post(url, json=pool)
        output = response.json()

        assert response.status_code == 201
        assert output["uuid"] == pool["uuid"]

    def test_hyper_update(
        self,
        pool_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        pool = pool_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "hypervisors"])

        response = client.post(url, json=pool)
        output = response.json()

        assert response.status_code == 201

        update = {"name": "foo", "description": "bar"}
        url = client.build_resource_uri(
            ["compute", "hypervisors", pool["uuid"]]
        )
        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["name"] == "foo"
        assert output["description"] == "bar"

    def test_hyper_delete(
        self,
        pool_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        pool = pool_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "hypervisors"])

        response = client.post(url, json=pool)

        assert response.status_code == 201

        url = client.build_resource_uri(
            ["compute", "hypervisors", pool["uuid"]]
        )
        response = client.delete(url)

        assert response.status_code == 204

        with pytest.raises(bazooka_exc.NotFoundError):
            client.get(url)

    # Machines

    def test_machines_add(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        machine = machine_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "machines"])

        response = client.post(url, json=machine)
        output = response.json()

        assert response.status_code == 201
        assert self._machine_cmp_shallow(machine, output)

    def test_machines_add_several(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        machines = [machine_factory(name=f"machine{i}") for i in range(3)]
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "machines"])

        for machine in machines:
            response = client.post(url, json=machine)
            output = response.json()
            assert response.status_code == 201
            assert self._machine_cmp_shallow(machine, output)

        response = client.get(url)
        output = response.json()
        assert len(output) == len(machines)
        for machine in machines:
            assert any(
                self._machine_cmp_shallow(machine, item) for item in output
            )

    def test_machines_update(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        machine = machine_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "machines"])

        response = client.post(url, json=machine)
        output = response.json()
        assert response.status_code == 201

        update = {"cores": 2, "ram": 2048}
        url = client.build_resource_uri(
            ["compute", "machines", machine["uuid"]]
        )

        response = client.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["cores"] == 2
        assert output["ram"] == 2048

    def test_machines_delete(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
    ):
        machine = machine_factory()
        client = user_api_client(auth_user_admin)
        url = client.build_collection_uri(["compute", "machines"])

        response = client.post(url, json=machine)

        assert response.status_code == 201

        url = client.build_resource_uri(
            ["compute", "machines", machine["uuid"]]
        )

        response = client.delete(url)

        assert response.status_code == 204

        with pytest.raises(bazooka_exc.NotFoundError):
            client.get(url)

    def test_newcomer_no_access(
        self,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        auth_test1_user: iam_clients.GenesisCoreAuth,
    ):
        admin_client = user_api_client(auth_user_admin)

        node = node_factory()
        node_uuid = node["uuid"]
        url = admin_client.build_collection_uri(["compute", "nodes"])
        response = admin_client.post(url, json=node)

        assert response.status_code == 201

        client = user_api_client(auth_test1_user)

        node = node_factory()
        url = client.build_collection_uri(["compute", "nodes"])

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.get(url)

        with pytest.raises(bazooka_exc.ForbiddenError):
            client.post(url, json=node)

        url = client.build_resource_uri(["compute", "nodes", node_uuid])
        with pytest.raises(bazooka_exc.ForbiddenError):
            client.delete(url)

        url = admin_client.build_collection_uri(["compute", "nodes"])
        response = admin_client.get(url)

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_owner_has_access(
        self,
        node_factory: tp.Callable,
        user_api_client: iam_clients.GenesisCoreTestRESTClient,
        auth_user_admin: iam_clients.GenesisCoreAuth,
        auth_test1_p1_user: iam_clients.GenesisCoreAuth,
    ):
        admin_client = user_api_client(auth_user_admin)
        admin_client.bind_role_to_user(
            # Owner role
            "726f6c65-0000-0000-0000-000000000002",
            auth_test1_p1_user.uuid,
            auth_test1_p1_user.project_id,
        )

        client = user_api_client(auth_test1_p1_user)
        node = node_factory(
            project_id=sys_uuid.UUID(auth_test1_p1_user.project_id)
        )
        node_uuid = node["uuid"]
        url = client.build_collection_uri(["compute", "nodes"])
        response = admin_client.post(url, json=node)

        assert response.status_code == 201

        url = client.build_collection_uri(["compute", "nodes"])
        response = client.get(url)
        assert response.status_code == 200

        output = response.json()
        assert len(output) == 1
        assert self._node_cmp_shallow(node, output[0])

        url = client.build_resource_uri(["compute", "nodes", node_uuid])
        response = client.delete(url)
        assert response.status_code == 204
