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
import uuid as sys_uuid
from urllib.parse import urljoin

import requests

from genesis_core.tests.functional import utils as test_utils


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

    def test_version(self, user_api: test_utils.RestServiceTestCase):
        response = requests.get(user_api.base_url)
        assert response.status_code == 200

    # Nodes

    def test_nodes_list(self, user_api: test_utils.RestServiceTestCase):
        url = urljoin(user_api.base_url, "nodes/")

        response = requests.get(url)

        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_nodes_add(
        self,
        node_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        node = node_factory()

        url = urljoin(user_api.base_url, "nodes/")
        response = requests.post(url, json=node)
        output = response.json()

        assert response.status_code == 201
        assert self._node_cmp_shallow(node, output)

    def test_nodes_add_several(
        self,
        node_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        nodes = [node_factory(name=f"node{i}") for i in range(3)]

        url = urljoin(user_api.base_url, "nodes/")
        for node in nodes:
            response = requests.post(url, json=node)
            output = response.json()
            assert response.status_code == 201
            assert self._node_cmp_shallow(node, output)

        url = urljoin(user_api.base_url, "nodes/")
        response = requests.get(url)
        output = response.json()
        assert len(output) == len(nodes)
        for node in nodes:
            assert any(self._node_cmp_shallow(node, item) for item in output)

    def test_nodes_update(
        self,
        node_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        node = node_factory()

        url = urljoin(user_api.base_url, "nodes/")
        response = requests.post(url, json=node)
        output = response.json()
        assert response.status_code == 201

        update = {"cores": 2, "ram": 2048}
        url = urljoin(user_api.base_url, f"nodes/{node['uuid']}")
        response = requests.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["cores"] == 2
        assert output["ram"] == 2048

    def test_nodes_delete(
        self,
        user_api: test_utils.RestServiceTestCase,
        node_factory: tp.Callable,
    ):
        node = node_factory()

        url = urljoin(user_api.base_url, "nodes/")
        response = requests.post(url, json=node)
        assert response.status_code == 201

        url = urljoin(user_api.base_url, f"nodes/{node['uuid']}")
        response = requests.delete(url)

        assert response.status_code == 204

        url = urljoin(user_api.base_url, f"nodes/{node['uuid']}")
        response = requests.get(url)

        assert response.status_code == 404

    def test_nodes_default_volume(
        self,
        user_api: test_utils.RestServiceTestCase,
        node_factory: tp.Callable,
    ):
        node = node_factory()

        url = urljoin(user_api.base_url, "nodes/")
        response = requests.post(url, json=node)
        output = response.json()

        assert response.status_code == 201
        assert output["root_disk_size"] == 15

    # Hypervisors

    def test_hyper_list_empty(self, user_api: test_utils.RestServiceTestCase):
        url = urljoin(user_api.base_url, "hypervisors/")

        response = requests.get(url)

        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_hyper_list(
        self,
        default_pool: tp.Dict[str, tp.Any],
        user_api: test_utils.RestServiceTestCase,
    ):
        url = urljoin(user_api.base_url, "hypervisors/")

        response = requests.get(url)
        output = response.json()

        assert response.status_code == 200
        assert len(output) == 1
        assert output[0]["uuid"] == default_pool["uuid"]

    def test_hyper_add(
        self,
        pool_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        pool = pool_factory()

        url = urljoin(user_api.base_url, "hypervisors/")
        response = requests.post(url, json=pool)
        output = response.json()

        assert response.status_code == 201
        assert output["uuid"] == pool["uuid"]

    def test_hyper_update(
        self,
        pool_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        pool = pool_factory()

        url = urljoin(user_api.base_url, "hypervisors/")
        response = requests.post(url, json=pool)
        output = response.json()

        assert response.status_code == 201

        update = {"name": "foo", "description": "bar"}
        url = urljoin(user_api.base_url, f"hypervisors/{pool['uuid']}")
        response = requests.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["name"] == "foo"
        assert output["description"] == "bar"

    def test_hyper_delete(
        self,
        pool_factory: tp.Callable,
        user_api: test_utils.RestServiceTestCase,
    ):
        pool = pool_factory()

        url = urljoin(user_api.base_url, "hypervisors/")
        response = requests.post(url, json=pool)

        assert response.status_code == 201

        url = urljoin(user_api.base_url, f"hypervisors/{pool['uuid']}")
        response = requests.delete(url)

        assert response.status_code == 204

        url = urljoin(user_api.base_url, f"hypervisors/{pool['uuid']}")
        response = requests.get(url)

        assert response.status_code == 404

    # Machines

    def test_machines_add(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api: test_utils.RestServiceTestCase,
    ):
        machine = machine_factory()

        url = urljoin(user_api.base_url, "machines/")
        response = requests.post(url, json=machine)
        output = response.json()

        assert response.status_code == 201
        assert self._machine_cmp_shallow(machine, output)

    def test_machines_add_several(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api: test_utils.RestServiceTestCase,
    ):
        machines = [machine_factory(name=f"machine{i}") for i in range(3)]

        url = urljoin(user_api.base_url, "machines/")
        for machine in machines:
            response = requests.post(url, json=machine)
            output = response.json()
            assert response.status_code == 201
            assert self._machine_cmp_shallow(machine, output)

        url = urljoin(user_api.base_url, "machines/")
        response = requests.get(url)
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
        user_api: test_utils.RestServiceTestCase,
    ):
        machine = machine_factory()

        url = urljoin(user_api.base_url, "machines/")
        response = requests.post(url, json=machine)
        output = response.json()
        assert response.status_code == 201

        update = {"cores": 2, "ram": 2048}
        url = urljoin(user_api.base_url, f"machines/{machine['uuid']}")
        response = requests.put(url, json=update)
        output = response.json()

        assert response.status_code == 200
        assert output["cores"] == 2
        assert output["ram"] == 2048

    def test_machines_delete(
        self,
        machine_factory: tp.Callable,
        default_pool: tp.Dict[str, tp.Any],
        user_api: test_utils.RestServiceTestCase,
    ):
        machine = machine_factory()

        url = urljoin(user_api.base_url, "machines/")
        response = requests.post(url, json=machine)
        assert response.status_code == 201

        url = urljoin(user_api.base_url, f"machines/{machine['uuid']}")
        response = requests.delete(url)

        assert response.status_code == 204

        url = urljoin(user_api.base_url, f"machines/{machine['uuid']}")
        response = requests.get(url)

        assert response.status_code == 404
