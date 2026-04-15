#    Copyright 2025-2026 Genesis Corporation.
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
import pwd
import grp
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
from genesis_core.common import log as infra_log
from genesis_core.compute.dm import models
from genesis_core.compute.node_set.dm import models as node_set_models
from genesis_core.common import constants as c
from genesis_core.secret import utils as secret_utils
from genesis_core.vs.dm import models as vs_models
from genesis_core.compute import constants as nc
from genesis_core.user_api.iam.dm import models as iam_models
from genesis_core.elements.dm import models as em_models


LOG = logging.getLogger(__name__)
USER = "ubuntu"
GCTL_CFG_DIR = f"/home/{USER}/.genesis"
SPEC_PATH = "/mnt/cdrom/spec.json"
MANIFEST_PATH = "/mnt/cdrom/core.yaml"
ECOSYSTEM_INSTANCE_MANIFEST_PATH = "/mnt/cdrom/ecosystem_instance.yaml"
MAIN_SUBNET_UUID = sys_uuid.UUID("c910a7e1-61ae-4d56-bdd6-a59faa3cbda3")


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
        "ecosystem_instance_manifest_path",
        default=ECOSYSTEM_INSTANCE_MANIFEST_PATH,
        help="Path to the ecosystem instance manifest",
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
    cfg.StrOpt(
        "hs256_jwks_encryption_key",
        default=c.DEFAULT_HS256_JWKS_ENCRYPTION_KEY,
        help="Encryption key for HS256 JWKS secret (A256GCM, 32 bytes)",
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


def _ensure_gctl_config(spec: dict[str, tp.Any]):
    """Ensure gctl configuration file exists."""
    if "admin_password" not in spec:
        raise RuntimeError("No admin password found in spec")

    admin_pass = spec["admin_password"]

    os.makedirs(GCTL_CFG_DIR, exist_ok=True)
    # chown GCTL_CFG_DIR to ubuntu user
    uid = pwd.getpwnam(USER).pw_uid
    gid = grp.getgrnam(USER).gr_gid
    os.chown(GCTL_CFG_DIR, uid, gid)

    config_path = os.path.join(GCTL_CFG_DIR, "genesisctl.yaml")
    with open(config_path, "w") as f:
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
    os.chown(config_path, uid, gid)
    os.system("genesis autocomplete")


def _install_element_manifest(
    spec: dict[str, tp.Any],
    element_name: str,
    manifest_path: str,
):
    """Idempotent element manifest installation."""
    element = em_models.Element.objects.get_one_or_none(
        filters={"name": dm_filters.EQ(element_name)}
    )

    if element is not None:
        LOG.info("Element %s already installed, skipping", element_name)
        return

    if not os.path.exists(manifest_path):
        LOG.info("No manifest file found at %s", manifest_path)
        return

    os.system(
        f"genesis --config {GCTL_CFG_DIR}/genesisctl.yaml elements install {manifest_path}"
    )


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
            filters={"uuid": dm_filters.EQ(c.VAR_CORE_IP_ADDRESS_UUID)}
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

    def _set_ecosystem_endpoint_var() -> bool:
        val_uuid = sys_uuid.UUID("0a810628-544e-4a1a-a895-d5e4176eec06")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Ecosystem endpoint variable already exists")
            return True

        LOG.info("Set ecosystem_endpoint variable")
        ecosystem_endpoint_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_ECOSYSTEM_ENDPOINT_UUID)}
        )
        if not ecosystem_endpoint_var:
            return False

        endpoint_value = spec.get("ecosystem_endpoint", "")
        ecosystem_endpoint_value = vs_models.Value(
            uuid=val_uuid,
            variable=ecosystem_endpoint_var,
            value=endpoint_value,
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        ecosystem_endpoint_value.insert()
        return True

    def _set_disable_telemetry_var() -> bool:
        val_uuid = sys_uuid.UUID("4c4b1ce8-4d39-4000-a826-098053d796e4")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Disable telemetry variable already exists")
            return True

        LOG.info("Set disable_telemetry variable")
        disable_telemetry_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_DISABLE_TELEMETRY_UUID)}
        )
        if not disable_telemetry_var:
            return False

        # Get disable telemetry flag from spec or use default False
        telemetry_value = spec.get("disable_telemetry", False)

        disable_telemetry_value = vs_models.Value(
            uuid=val_uuid,
            variable=disable_telemetry_var,
            value=telemetry_value,
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        disable_telemetry_value.insert()
        return True

    def _set_realm_uuid_var() -> bool:
        val_uuid = sys_uuid.UUID("f134c97f-bb4d-4d67-9527-8c90e2f04f8c")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Stand UUID variable already exists")
            return True

        LOG.info("Set realm_uuid variable")
        realm_uuid_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_REALM_UUID_UUID)}
        )
        if not realm_uuid_var:
            return False

        # Get stand UUID from spec
        realm_uuid_value = spec.get("realm_uuid", "")
        if not realm_uuid_value:
            LOG.warning("No stand UUID found in spec")
            return True

        realm_uuid_val = vs_models.Value(
            uuid=val_uuid,
            variable=realm_uuid_var,
            value=realm_uuid_value,
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        realm_uuid_val.insert()
        return True

    def _set_realm_secret_var() -> bool:
        val_uuid = sys_uuid.UUID("c5548ad1-7990-4283-ba1f-725fd7a7b9d4")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Stand secret variable already exists")
            return True

        LOG.info("Set realm_secret variable")
        realm_secret_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_REALM_SECRET_UUID)}
        )
        if not realm_secret_var:
            return False

        # Get stand secret from spec
        realm_secret_value = spec.get("realm_secret", "")
        if not realm_secret_value:
            LOG.warning("No stand secret found in spec")
            return True

        realm_secret_val = vs_models.Value(
            uuid=val_uuid,
            variable=realm_secret_var,
            value=realm_secret_value,
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        realm_secret_val.insert()
        return True

    def _set_realm_access_token_var() -> bool:
        val_uuid = sys_uuid.UUID("2e0a0f6f-0568-4804-91d2-1f68f43afda9")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Stand access token variable already exists")
            return True

        LOG.info("Set realm_access_token variable")
        realm_access_token_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_REALM_ACCESS_TOKEN_UUID)}
        )
        if not realm_access_token_var:
            return False

        # Get stand access token from spec (could be a dict or string)
        token_value = spec.get("realm_tokens", {})
        if not token_value:
            LOG.warning("No stand access token found in spec")
            return True

        realm_access_token_val = vs_models.Value(
            uuid=val_uuid,
            variable=realm_access_token_var,
            value=token_value.get("access_token", ""),
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        realm_access_token_val.insert()
        return True

    def _set_realm_refresh_token_var() -> bool:
        val_uuid = sys_uuid.UUID("eacf0c1f-3495-4986-89a5-80139526b82a")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("Stand refresh token variable already exists")
            return True

        LOG.info("Set realm_refresh_token variable")
        realm_refresh_token_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_REALM_REFRESH_TOKEN_UUID)}
        )
        if not realm_refresh_token_var:
            return False

        # Get stand refresh token from spec (could be a dict or string)
        token_value = spec.get("realm_tokens", {})
        if not token_value:
            LOG.warning("No stand refresh token found in spec")
            return True

        realm_refresh_token_val = vs_models.Value(
            uuid=val_uuid,
            variable=realm_refresh_token_var,
            value=token_value.get("refresh_token", ""),
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        realm_refresh_token_val.insert()
        return True

    def _set_hs256_jwks_encryption_key_var() -> bool:
        val_uuid = sys_uuid.UUID("b16ba886-c18d-4842-9815-ba09d2aae2cb")
        existing_value = vs_models.Value.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(val_uuid)}
        )
        if existing_value:
            LOG.info("HS256 JWKS encryption key variable already exists")
            return True

        LOG.info("Set hs256_jwks_encryption_key variable")
        hs256_var = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(c.VAR_HS256_JWKS_ENCRYPTION_KEY_UUID)}
        )
        if not hs256_var:
            return False

        key_value = CONF["iam"].hs256_jwks_encryption_key
        if not key_value:
            LOG.warning("No HS256 JWKS encryption key provided")
            return True

        hs256_val = vs_models.Value(
            uuid=val_uuid,
            variable=hs256_var,
            value=key_value,
            project_id=c.EM_HIDDEN_PROJECT_ID,
        )
        hs256_val.insert()
        return True

    tasks = [
        _activate_profile,
        _set_core_ip_var,
        _set_ecosystem_endpoint_var,
        _set_disable_telemetry_var,
        _set_realm_uuid_var,
        _set_realm_secret_var,
        _set_realm_access_token_var,
        _set_realm_refresh_token_var,
        _set_hs256_jwks_encryption_key_var,
    ]

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

    # Configure logging
    infra_log.configure()

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
            _ensure_gctl_config(spec)
            _install_element_manifest(spec, "core", CONF.manifest_path)
            _install_element_manifest(
                spec,
                "ecosystem_instance",
                CONF.ecosystem_instance_manifest_path,
            )
            _set_defaults(spec)
            return
        except Exception:
            LOG.exception("Unable to perform bootstrap, retrying...")
            if not retry_on_error:
                return

        time.sleep(2.0)


if __name__ == "__main__":
    main()
