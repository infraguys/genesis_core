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

from __future__ import annotations

import os
import typing as tp
import uuid as sys_uuid

import pytest
import netaddr
from gcl_iam import algorithms
from gcl_iam.tests.functional import clients as iam_clients
from gcl_sdk.events import clients as sdk_clients

from genesis_core.common import constants as c
from genesis_core.common import utils
from genesis_core.node import constants as nc
from genesis_core.node.dm import models as node_models
from genesis_core.node.node_set.dm import models as node_set_models
from genesis_core.user_api.api import app as user_app
from genesis_core.tests.functional import utils as test_utils
from genesis_core.config.dm import models as conf_models
from genesis_core.config import constants as cc
from genesis_core.secret import constants as sc
from genesis_core.secret.dm import models as secret_models
from genesis_core.user_api.iam.dm import models as iam_models

FIRST_MIGRATION = "0000-root-d34de1.py"


@pytest.fixture(scope="session")
def hs256_algorithm():
    secret = os.getenv("HS256_KEY", c.DEFAULT_HS256_KEY)
    return algorithms.HS256(key=secret)


@pytest.fixture(scope="session")
def context_storage(
    hs256_algorithm: algorithms.AbstractAlgorithm,
):
    return utils.get_context_storage(
        global_salt=os.getenv("GLOBAL_SALT", c.DEFAULT_GLOBAL_SALT),
        token_algorithm=hs256_algorithm,
        events_client=sdk_clients.DummyEventClient(),
    )


@pytest.fixture(scope="session")
def admin_username():
    return c.DEFAULT_ADMIN_USERNAME


@pytest.fixture(scope="session")
def admin_password():
    return os.getenv("ADMIN_PASSWORD", c.DEFAULT_ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def default_client_id():
    return c.DEFAULT_CLIENT_ID


@pytest.fixture(scope="session")
def default_client_secret():
    return os.getenv("DEFAULT_CLIENT_SECRET", c.DEFAULT_CLIENT_SECRET)


@pytest.fixture(scope="session")
def default_client_uuid():
    return c.DEFAULT_CLIENT_UUID


@pytest.fixture(scope="module")
def user_api_service(hs256_algorithm, context_storage):
    class ApiRestService(test_utils.RestServiceTestCase):
        __FIRST_MIGRATION__ = FIRST_MIGRATION
        __APP__ = user_app.build_wsgi_application(
            context_storage=context_storage,
            token_algorithm=hs256_algorithm,
        )

    rest_service = ApiRestService()
    rest_service.setup_class()

    yield rest_service

    rest_service.teardown_class()


@pytest.fixture()
def user_api(user_api_service: test_utils.RestServiceTestCase):
    user_api_service.setup_method()

    yield user_api_service

    user_api_service.teardown_method()


@pytest.fixture()
def auth_user_admin(
    admin_username: str,
    admin_password: str,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    return iam_clients.GenesisCoreAuth(
        username=admin_username,
        password=admin_password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
    )


@pytest.fixture()
def auth_test1_user(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    password = "test1test"
    client = user_api_client(auth_user_admin)
    user = client.create_user(username="test1", password=password)
    user_obj = iam_models.User.objects.get_one(filters={"uuid": user["uuid"]})
    client.confirm_email(
        user_uuid=user_obj.uuid,
        code=str(user_obj.confirmation_code),
    )

    return iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
    )


@pytest.fixture()
def auth_test2_user(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    password = "test2test"
    client = user_api_client(auth_user_admin)
    user = client.create_user(username="test2", password=password)
    user_obj = iam_models.User.objects.get_one(filters={"uuid": user["uuid"]})
    client.confirm_email(
        user_uuid=user_obj.uuid,
        code=str(user_obj.confirmation_code),
    )

    return iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
    )


@pytest.fixture()
def auth_test1_p1_user(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    password = "testtest1p1"
    client = user_api_client(auth_user_admin)
    user = client.create_user(username="test1p1", password=password)
    user_obj = iam_models.User.objects.get_one(filters={"uuid": user["uuid"]})
    client.confirm_email(
        user_uuid=user_obj.uuid,
        code=str(user_obj.confirmation_code),
    )

    auth = iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
        project_id=None,
    )

    client = user_api_client(auth)

    org = client.create_organization(name="OrganizationU1P1")
    project = client.create_project(
        uuid=str(sys_uuid.uuid4()),
        organization_uuid=org["uuid"],
        name="ProjectU1P1",
    )

    return iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
        project_id=project["uuid"],
    )


@pytest.fixture()
def auth_test2_p1_user(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    default_client_uuid: str,
    default_client_id: str,
    default_client_secret: str,
):
    password = "testtest2p1"
    client = user_api_client(auth_user_admin)
    user = client.create_user(username="test2p1", password=password)
    user_obj = iam_models.User.objects.get_one(filters={"uuid": user["uuid"]})
    client.confirm_email(
        user_uuid=user_obj.uuid,
        code=str(user_obj.confirmation_code),
    )

    auth = iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
        project_id=None,
    )

    client = user_api_client(auth)

    org = client.create_organization(name="OrganizationU2P1")
    project = client.create_project(
        uuid=str(sys_uuid.uuid4()),
        organization_uuid=org["uuid"],
        name="ProjectU2P1",
    )

    return iam_clients.GenesisCoreAuth(
        username=user["username"],
        password=password,
        client_uuid=default_client_uuid,
        client_id=default_client_id,
        client_secret=default_client_secret,
        uuid=user["uuid"],
        email=user["email"],
        project_id=project["uuid"],
    )


@pytest.fixture()
def user_api_client(user_api, auth_user_admin):

    def build_client(
        auth: iam_clients.GenesisCoreAuth,
        permissions: list[str] = None,
        project_id: str = None,
    ):
        permissions = permissions or []
        client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth,
        )
        admin_client = iam_clients.GenesisCoreTestRESTClient(
            f"{user_api.get_endpoint()}v1/",
            auth_user_admin,
        )

        admin_client.set_permissions_to_user(
            user_uuid=auth.uuid,
            permissions=permissions,
            project_id=project_id,
        )

        return client

    return build_client


@pytest.fixture()
def user_api_noauth_client(user_api):
    return lambda: iam_clients.GenesisCoreTestNoAuthRESTClient(
        f"{user_api.get_endpoint()}v1/"
    )


@pytest.fixture
def machine_agent_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "agent",
        status: str = nc.MachineAgentStatus.ACTIVE.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        obj = node_models.MachineAgent(
            uuid=uuid,
            name=name,
            status=status,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def node_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "node",
        cores: int = 1,
        ram: int = 1024,
        image: str = "ubuntu_24.04",
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = nc.NodeStatus.NEW.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        node = node_models.Node(
            uuid=uuid,
            name=name,
            cores=cores,
            ram=ram,
            image=image,
            project_id=project_id,
            status=status,
            **kwargs,
        )
        view = node.dump_to_simple_view()
        view.pop("node_set")
        return view

    return factory


@pytest.fixture
def node_set_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "node_set",
        cores: int = 1,
        ram: int = 1024,
        image: str = "ubuntu_24.04",
        replicas: int = 1,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = nc.NodeStatus.NEW.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        obj = node_set_models.NodeSet(
            uuid=uuid,
            name=name,
            cores=cores,
            ram=ram,
            image=image,
            replicas=replicas,
            project_id=project_id,
            status=status,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def pool_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        agent: sys_uuid.UUID | None = None,
        name: str = "pool-default",
        driver_spec: dict | None = None,
        status: str = nc.MachinePoolStatus.ACTIVE.value,
        avail_cores: int = 8,
        avail_ram: int = 16384,
        all_cores: int = 8,
        all_ram: int = 16384,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        driver_spec = (
            {"driver": "libvirt"} if driver_spec is None else driver_spec
        )
        pool = node_models.MachinePool(
            uuid=uuid,
            agent=agent,
            name=name,
            status=status,
            driver_spec=driver_spec,
            avail_cores=avail_cores,
            avail_ram=avail_ram,
            all_cores=all_cores,
            all_ram=all_ram,
            **kwargs,
        )
        view = pool.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def machine_factory(default_pool: tp.Dict[str, tp.Any]):
    def factory(
        uuid: sys_uuid.UUID | None = None,
        pool: sys_uuid.UUID | None = None,
        name: str = "node",
        cores: int = 1,
        ram: int = 1024,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = nc.MachineStatus.ACTIVE.value,
        build_status: str = nc.MachineBuildStatus.READY.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        pool = pool or sys_uuid.UUID(default_pool["uuid"])
        machine = node_models.Machine(
            uuid=uuid,
            pool=pool,
            name=name,
            cores=cores,
            ram=ram,
            project_id=project_id,
            status=status,
            build_status=build_status,
            **kwargs,
        )
        view = machine.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def config_factory():
    def factory(
        target_node: sys_uuid.UUID,
        uuid: sys_uuid.UUID | None = None,
        name: str = "config",
        path: str = "/etc/genesis-configs/config.conf",
        content_body: str = "test",
        on_change_cmd: str | None = None,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: str = cc.ConfigStatus.NEW.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        target = conf_models.NodeTarget.from_node(target_node)
        body = conf_models.TextBodyConfig.from_text(content_body)
        if on_change_cmd is None:
            on_change = conf_models.OnChangeNoAction()
        else:
            on_change = conf_models.OnChangeShell.from_command(on_change_cmd)

        config = conf_models.Config(
            uuid=uuid,
            name=name,
            path=path,
            target=target,
            body=body,
            on_change=on_change,
            project_id=project_id,
            status=status,
            **kwargs,
        )
        view = config.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def password_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "password",
        constructor: secret_models.AbstractSecretConstructor | None = None,
        method: sc.SecretMethod = sc.SecretMethod.AUTO_HEX,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: cc.ConfigStatus | None = None,
        value: str | None = None,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        constructor = (
            secret_models.PlainSecretConstructor()
            if constructor is None
            else constructor
        )
        status_value = (
            cc.ConfigStatus.NEW.value if status is None else status.value
        )
        obj = secret_models.Password(
            uuid=uuid,
            name=name,
            method=method.value,
            project_id=project_id,
            status=status_value,
            constructor=constructor,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        if status is None:
            view.pop("status")
        if value is None:
            view.pop("value")
        return view

    return factory


@pytest.fixture
def cert_factory():
    def factory(
        uuid: sys_uuid.UUID | None = None,
        name: str = "cert",
        domains: tp.Collection[str] = ("genesis-core.tech",),
        email: str = "user@genesis-core.tech",
        key: str | None = None,
        cert: str | None = None,
        constructor: secret_models.AbstractSecretConstructor | None = None,
        method: secret_models.AbstractCertificateMethod | None = None,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: cc.ConfigStatus | None = None,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        constructor = (
            secret_models.PlainSecretConstructor()
            if constructor is None
            else constructor
        )
        method = (
            secret_models.DNSCoreCertificateMethod()
            if method is None
            else method
        )
        status_value = (
            cc.ConfigStatus.NEW.value if status is None else status.value
        )
        obj = secret_models.Certificate(
            uuid=uuid,
            name=name,
            method=method,
            project_id=project_id,
            status=status_value,
            constructor=constructor,
            domains=list(domains),
            email=email,
            key=key,
            cert=cert,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        if status is None:
            view.pop("status")
        if key is None:
            view.pop("key")
        if cert is None:
            view.pop("cert")
        view.pop("expiration_threshold")
        view.pop("overcome_threshold")

        return view

    return factory


@pytest.fixture
def ssh_key_factory():
    def factory(
        target_node: sys_uuid.UUID,
        target_public_key: str,
        uuid: sys_uuid.UUID | None = None,
        name: str = "key",
        constructor: secret_models.AbstractSecretConstructor | None = None,
        project_id: sys_uuid.UUID = c.SERVICE_PROJECT_ID,
        status: cc.ConfigStatus | None = None,
        user: str = "root",
        authorized_keys=".ssh/authorized_keys",
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        target = conf_models.NodeTarget.from_node(target_node)
        constructor = (
            secret_models.PlainSecretConstructor()
            if constructor is None
            else constructor
        )
        status_value = (
            cc.ConfigStatus.NEW.value if status is None else status.value
        )
        obj = secret_models.SSHKey(
            uuid=uuid,
            name=name,
            project_id=project_id,
            status=status_value,
            constructor=constructor,
            target=target,
            user=user,
            authorized_keys=authorized_keys,
            target_public_key=target_public_key,
            **kwargs,
        )
        view = obj.dump_to_simple_view()
        if status is None:
            view.pop("status")

        return view

    return factory


@pytest.fixture
def builder_factory() -> tp.Callable:
    def factory(
        uuid: sys_uuid.UUID | None = None,
        status: str = nc.BuilderStatus.ACTIVE.value,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        builder = node_models.Builder(
            uuid=uuid,
            status=status,
            **kwargs,
        )
        view = builder.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def interface_factory() -> tp.Callable:
    def factory(
        uuid: sys_uuid.UUID | None = None,
        mac: str | None = None,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        interface = node_models.Interface(
            uuid=uuid,
            mac=mac or node_models.Port.generate_mac(),
            **kwargs,
        )
        view = interface.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def machine_pool_reservation_factory() -> tp.Callable:
    def factory(
        pool: sys_uuid.UUID,
        uuid: sys_uuid.UUID | None = None,
        machine: sys_uuid.UUID | None = None,
        cores: int = 1,
        ram: int = 1024,
        **kwargs,
    ) -> tp.Dict[str, tp.Any]:
        uuid = uuid or sys_uuid.uuid4()
        reservation = node_models.MachinePoolReservations(
            uuid=uuid,
            pool=pool,
            machine=machine,
            cores=cores,
            ram=ram,
            **kwargs,
        )
        view = reservation.dump_to_simple_view()
        return view

    return factory


@pytest.fixture
def default_machine_agent(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
    machine_agent_factory: tp.Callable,
):
    uuid = sys_uuid.UUID("00000000-1110-0000-0000-000000000000")
    default_agent = machine_agent_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["machine_agents"])
    client.post(url, json=default_agent)

    yield default_agent

    url = client.build_resource_uri(["machine_agents", uuid])
    client.delete(url)


@pytest.fixture()
def default_pool(
    pool_factory: tp.Callable,
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
):
    uuid = sys_uuid.UUID("00000000-1111-0000-0000-000000000000")
    default_pool = pool_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["hypervisors"])
    client.post(url, json=default_pool)

    return default_pool


@pytest.fixture
def default_node(
    node_factory: tp.Callable,
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
):
    uuid = sys_uuid.UUID("00000000-1112-0000-0000-000000000000")
    default_node = node_factory(uuid=uuid)
    client = user_api_client(auth_user_admin)
    url = client.build_collection_uri(["nodes"])
    client.post(url, json=default_node)

    yield default_node

    url = client.build_resource_uri(["nodes", uuid])
    client.delete(url)


@pytest.fixture
def default_network(
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
) -> node_models.Network:
    uuid = sys_uuid.UUID("00000000-1112-0100-0000-000000000000")
    network = node_models.Network(
        uuid=uuid,
        driver_spec={"driver": "dummy"},
        project_id=c.SERVICE_PROJECT_ID,
    )
    network.insert()

    return network


@pytest.fixture
def default_subnet(
    default_network: node_models.Network,
    user_api_client: iam_clients.GenesisCoreTestRESTClient,
    auth_user_admin: iam_clients.GenesisCoreAuth,
) -> node_models.Subnet:
    uuid = sys_uuid.UUID("00000000-1112-0130-0000-000000000000")
    subnet = node_models.Subnet(
        uuid=uuid,
        network=default_network.uuid,
        cidr=netaddr.IPNetwork("10.0.0.0/24"),
        project_id=c.SERVICE_PROJECT_ID,
    )
    subnet.insert()

    return subnet
