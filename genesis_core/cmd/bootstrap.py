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

import json
import ipaddress
import logging
import os
import sys
import time
import typing as tp
import uuid as sys_uuid

import yaml
from oslo_config import cfg
from restalchemy.storage.sql import engines
from restalchemy.dm import filters as dm_filters
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.common import config_opts as ra_config_opts
from gcl_sdk.infra.dm import models as infra_models

from genesis_core.common import config
from genesis_core.compute.dm import models
from genesis_core.compute.node_set.dm import models as node_set_models
from genesis_core.common import constants as c
from genesis_core.secret import utils as secret_utils
from genesis_core.vs.dm import models as vs_models
from genesis_core.compute import constants as nc
from genesis_core.user_api.iam.dm import models as iam_models
from genesis_core.elements.dm import models as em_models


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
GCTL_CFG_DIR = "/home/ubuntu/.genesis"
SPEC_PATH = "/mnt/cdrom/spec.json"
MANIFEST_PATH = "/mnt/cdrom/core.yaml"
MAIN_SUBNET_UUID = sys_uuid.UUID("c910a7e1-61ae-4d56-bdd6-a59faa3cbda3")
VAR_CORE_IP_ADDRESS_UUID = sys_uuid.UUID("55814431-ede5-4c4e-abd6-e61600a3069b")


cli_opts = [
    cfg.BoolOpt(
        "retry_on_error",
        default=True,
        help="Should the script retry on errors",
    ),
    cfg.StrOpt(
        "manifest_path",
        default=MANIFEST_PATH,
        help="Path to the core manifest",
    ),
    cfg.StrOpt(
        "core_endpoint",
        default="http://localhost:11010",
        help="Core endpoint",
    ),
    cfg.StrOpt(
        "core_user",
        default="admin",
        help="Core user",
    ),
]

iam_opts = [
    cfg.StrOpt(
        "global_salt",
        default=None,
        help="Global salt for IAM",
    ),
    cfg.StrOpt(
        "client_secret",
        default="GenesisCoreSecret",
        help="Client secret for IAM",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)
CONF.register_cli_opts(iam_opts, "iam")
ra_config_opts.register_posgresql_db_opts(CONF)


def _net_range(network: ipaddress.IPv4Network, start_offset: int) -> str:
    first = network.network_address + start_offset
    size = int(network.num_addresses * 0.6) - (int(network.num_addresses * 0.6) % 10)
    last = min(first + max(size - 1, 0), network.broadcast_address - 1)
    return f"{first}-{last}"


def _apply_flat_network(stand: dict[str, tp.Any]) -> None:
    """Apply flat network configuration idempotently.

    The simplest implementation as we expect only one flat network that is created
    during the bootstrap process.
    """

    networks = models.Network.objects.get_all()
    if networks:
        LOG.info("Flat network already exists")
        return

    # Create flat network
    network_cfg = {
        "name": "flat",
        "uuid": "1d4f64db-817a-4862-a588-c9e950823cc1",
        "driver_spec": {
            "driver": "flat_bridge",
            "dhcp_cfg": "/etc/dhcp/dhcpd.conf",
        },
        "project_id": c.SERVICE_PROJECT_ID,
    }
    network = models.Network.restore_from_simple_view(**network_cfg)

    network.insert()
    LOG.info("Created network %s", network.uuid)

    #
    main_net = ipaddress.ip_network(stand["network"]["cidr"])
    boot_net = ipaddress.ip_network(stand["boot_network"]["cidr"])

    subnets = [
        {
            "name": stand["network"]["name"],
            "uuid": str(MAIN_SUBNET_UUID),
            "cidr": stand["network"]["cidr"],
            "ip_range": _net_range(main_net, 20),
            "ip_discovery_range": None,
            "dhcp": bool(stand["network"].get("dhcp", False)),
            "dns_servers": [str(main_net.network_address + 2)],
            "routers": [
                {
                    "to": "0.0.0.0/0",
                    "via": str(main_net.network_address + 1),
                }
            ],
            "next_server": None,
            "project_id": c.SERVICE_PROJECT_ID,
        },
        {
            "name": stand["boot_network"]["name"],
            "uuid": "86b2d256-079a-460e-a78f-bc9a7b4b2996",
            "cidr": stand["boot_network"]["cidr"],
            "ip_range": None,
            "ip_discovery_range": _net_range(boot_net, 10),
            "dhcp": bool(stand["boot_network"].get("dhcp", False)),
            "dns_servers": [str(main_net.network_address + 2)],
            "routers": [
                {
                    "to": "0.0.0.0/0",
                    "via": str(boot_net.network_address + 2),
                }
            ],
            "next_server": str(boot_net.network_address + 2),
            "project_id": c.SERVICE_PROJECT_ID,
        },
    ]

    for subnet_data in subnets:
        subnet = models.Subnet.restore_from_simple_view(**subnet_data)
        subnet.network = network.uuid
        subnet.insert()
        LOG.info("Created subnet %s", subnet.uuid)


def _apply_startup_db(spec: dict[str, tp.Any]) -> None:
    """Idempotent startup database configuration."""
    stand = spec.get("stand", {})
    if not stand:
        LOG.info("No `stand` section found in %s", spec)
        return

    # Apply flat network configuration
    _apply_flat_network(stand)

    # Apply machine pools
    # NOTE(akremenetsky): It maybe a problem for large installations
    # with many machine pools, but it's fine for now.
    machine_pools = models.MachinePool.objects.get_all()

    for hypervisor in stand.get("hypervisors", []):
        hypervisor["iface_mtu"] = 1500
        pool_data = {
            "name": "hypervisor",
            "machine_type": "VM",
            "driver_spec": hypervisor,
        }
        pool = models.MachinePool.restore_from_simple_view(**pool_data)

        # Skip if the pool already exists
        for _pool in machine_pools:
            if (
                _pool.driver_spec["connection_uri"]
                == pool.driver_spec["connection_uri"]
            ):
                break
        else:
            # Pool does not exist, create it
            try:
                pool.insert()
            except ra_exceptions.ConflictRecords:
                LOG.info("Machine pool %s already exists", pool.uuid)
            else:
                LOG.info("Created machine pool %s", pool.uuid)
            continue

        LOG.info("Machine pool %s already exists, skipping", pool.uuid)


def _install_core_manifest(spec: dict[str, tp.Any], core_element_name: str = "core"):
    """Idempotent core manifest installation."""
    core_element = em_models.Element.objects.get_one_or_none(
        filters={"name": dm_filters.EQ(core_element_name)}
    )

    if core_element is not None:
        LOG.info("Core element %s already installed, skipping", core_element_name)
        return

    manifest_path = CONF.manifest_path
    if not os.path.exists(manifest_path):
        LOG.info("No manifest file found at %s", manifest_path)
        return

    if "admin_password" not in spec:
        raise RuntimeError("No admin password found in spec")

    admin_pass = spec["admin_password"]

    # Create a configuration file for gctl
    os.makedirs(GCTL_CFG_DIR, exist_ok=True)
    with open(os.path.join(GCTL_CFG_DIR, "genesisctl.yaml"), "w") as f:
        yaml.safe_dump(
            {
                "schema_version": 1,
                "realms": {
                    "default-realm": {
                        "endpoint": CONF.core_endpoint,
                        "check_updates": True,
                        "contexts": {
                            "default-context": {
                                "user": CONF.core_user,
                                "password": admin_pass,
                            },
                        },
                        "current-context": "default-context",
                    }
                },
                "current-realm": "default-realm",
            },
            f,
        )

    os.system(f"genesis --config {GCTL_CFG_DIR}/genesisctl.yaml elements install {manifest_path}")


def _init_secrets(spec: dict[str, tp.Any]):
    """Idempotent secrets initialization."""
    # Check if the secrets are already initialized
    default_client = iam_models.IamClient.objects.get_one_or_none(
        filters={"salt": dm_filters.EQ(c.DEFAULT_ADMIN_SALT)}
    )
    if default_client is None:
        LOG.info(
            "IAM client with default salt not found, secrets initialization skipped"
        )
        return

    global_salt = CONF["iam"].global_salt
    if not global_salt:
        raise ValueError("Global salt is not provided")

    if "admin_password" not in spec:
        raise RuntimeError("No admin password found in spec")

    admin_pass = spec["admin_password"]

    # Regenerate secrets for the default IAM client
    admin_salt = secret_utils.generate_salt()
    client_secret_hash = secret_utils.generate_hash_for_secret(
        secret=CONF["iam"].client_secret,
        secret_salt=admin_salt,
        global_salt=global_salt,
    )
    default_client.salt = admin_salt
    default_client.secret_hash = client_secret_hash
    default_client.save()

    # Regenerate secrets for the default IAM user
    admin_secret_hash = secret_utils.generate_hash_for_secret(
        secret=admin_pass,
        secret_salt=admin_salt,
        global_salt=global_salt,
    )
    default_user = iam_models.User.objects.get_one(
        filters={"salt": dm_filters.EQ(c.DEFAULT_ADMIN_SALT)}
    )
    default_user.salt = admin_salt
    default_user.secret_hash = admin_secret_hash
    default_user.save()


def _add_core_set(spec: dict[str, tp.Any]):
    """Idempotent core set and nodes addition.

    We need to add the core set and nodes to the database
    to make the bootstrap process idempotent. When the core manifest
    is installed, the core set and nodes will be detected on the data
    plane and won't be created again.
    """
    disks = []
    for idx, disk in enumerate(spec["stand"]["bootstraps"][0]["disks"]):
        # The first disk is the system disk with an image
        if idx == 0:
            disks.append(
                {
                    "size": disk["size"],
                    "label": disk["label"],
                    "image": spec["stand"]["bootstraps"][0]["image_uri"],
                }
            )
        else:
            disks.append({"size": disk["size"], "label": disk["label"]})

    node_set = node_set_models.NodeSet(
        uuid=c.CORE_SET_UUID,
        name="core-set",
        project_id=c.EM_PROJECT_ID,
        cores=spec["stand"]["bootstraps"][0]["cores"],
        ram=spec["stand"]["bootstraps"][0]["memory"],
        disk_spec=infra_models.SetDisksSpec(
            disks=disks,
        ),
        # It will be reworked after HA is implemented
        replicas=1,
    )
    try:
        node_set.insert()
    except ra_exceptions.ConflictRecords:
        LOG.info("Node set %s already exists", node_set.uuid)
        # Finish operation if the core set already exists
        return

    # Convert instance to resource
    node_set_resource = node_set.to_ua_resource()
    node_set_resource.insert()

    LOG.info("Created node set %s", node_set.uuid)

    # Add nodes
    nodes = node_set.gen_nodes(
        project_id=nc.NODE_SET_PROJECT,
        placement_policies=[],
        node_uuids=[sys_uuid.UUID(spec["stand"]["bootstraps"][0]["uuid"])],
    )

    prefix = spec["stand"]["hypervisors"][0]["machine_prefix"]
    for i, node in enumerate(nodes):
        bootstrap_spec = spec["stand"]["bootstraps"][i]

        # Special naming for core nodes
        node.name = f"{prefix}{str(node.uuid)[:8]}-{node.name}"
        node.insert()

        # Convert derivatives to resources
        node_resource = node.to_ua_resource(master=node_set_resource.uuid)
        node_resource.insert()
        LOG.info("Created node %s", node.uuid)

        # Create ports.
        for port in bootstrap_spec["ports"]:
            if not port.get("ip"):
                continue

            p = models.Port.restore_from_simple_view(
                **dict(
                    subnet=str(MAIN_SUBNET_UUID),
                    source=spec["stand"]["network"]["name"],
                    node=str(node.uuid),
                    ipv4=port["ip"],
                    mac=port["mac"],
                    status="ACTIVE",
                    project_id=str(c.SERVICE_PROJECT_ID),
                )
            )
            p.insert()


def _set_defaults(spec: dict[str, tp.Any]):
    """Set default values, profiles, etc."""

    # Activate default profile
    def _activate_profile() -> bool:
        # Check if there is already an active profile
        active_profile = vs_models.Profile.objects.get_one_or_none(
            filters={
                "active": dm_filters.EQ(True),
            },
        )
        if active_profile:
            LOG.info("Already has active profile: %s", active_profile.name)
            return True

        LOG.info("Activating default profile")
        profile = vs_models.Profile.objects.get_one_or_none(
            filters={
                "name": dm_filters.EQ(spec["profile"]),
            },
        )
        if profile:
            profile.activate()
            LOG.info("Activated profile: %s", profile.name)
            return True

        return False

    def _set_core_ip_var() -> bool:
        val_uuid = sys_uuid.UUID("0225c5ed-07db-45fe-8154-2b8b9cae388a")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Core IP address variable already exists")
            return True

        LOG.info("Set core_ip_address variable")
        core_ip_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(VAR_CORE_IP_ADDRESS_UUID)}
        )
        if not core_ip_var:
            return False

        core_ip_value = vs_models.Value(
            uuid=val_uuid,
            variable=core_ip_var,
            # Get IP from the main network
            value=spec["stand"]["bootstraps"][0]["ports"][0]["ip"],
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        core_ip_value.insert()
        return True

    tasks = [_activate_profile, _set_core_ip_var]

    # Perform all tasks to set default values until timeout
    timeout_at = time.monotonic() + 120
    while tasks:
        task = tasks[0]

        # Perform task
        try:
            completed = task()
        except Exception:
            completed = False
            LOG.exception(f"Unable to complete the task {task.__name__}")

        if completed:
            tasks.pop(0)
            continue

        if time.monotonic() > timeout_at:
            raise TimeoutError(f"Timeout reached to perform {task.__name__}")
        time.sleep(0.5)


def main() -> None:
    # Parse config
    config.parse(sys.argv[1:])

    retry_on_error = CONF.retry_on_error
    engines.engine_factory.configure_postgresql_factory(CONF)

    if not os.path.exists(SPEC_PATH):
        LOG.info("No spec file found at %s", SPEC_PATH)
        return

    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    while True:
        try:
            LOG.info("GC Bootstrap script")
            _apply_startup_db(spec)
            _init_secrets(spec)
            _add_core_set(spec)
            _install_core_manifest(spec)
            _set_defaults(spec)
            return
        except Exception:
            LOG.exception("Unable to perform bootstrap, retrying...")
            if not retry_on_error:
                return

        time.sleep(2.0)


if __name__ == "__main__":
    main()
