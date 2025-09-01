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

import sys
import time
import logging

import yaml
from oslo_config import cfg
from restalchemy.storage.sql import engines
from restalchemy.storage import exceptions as ra_exceptions
from restalchemy.common import config_opts as ra_config_opts
from gcl_sdk.clients.http import base as http_client
from genesis_ci_tools import elements

from genesis_core.common import config
from genesis_core.node.dm import models
from genesis_core.common import constants as c

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

cli_opts = [
    cfg.BoolOpt(
        "retry_on_error",
        default=True,
        help="Should the script retry on errors",
    ),
    cfg.StrOpt(
        "startup_db_path",
        default="/etc/genesis_core/startup_cfg.yaml",
        help="Path to the startup database",
    ),
    cfg.StrOpt(
        "manifest_path",
        default="/etc/genesis_core/core.yaml",
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
    cfg.StrOpt(
        "core_password",
        default="admin",
        help="Core password",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)
ra_config_opts.register_posgresql_db_opts(CONF)


def _apply_startup_db():
    with open(CONF.startup_db_path, "r") as f:
        data = yaml.safe_load(f)

    if "startup_entities" not in data:
        LOG.info("No startup entities found")
        return

    # Handle networks
    startup_entities = data["startup_entities"]
    for network in startup_entities.get("networks", []):
        subnets = network.pop("subnets", [])
        net_project_id = network.pop("project_id", c.SERVICE_PROJECT_ID)
        network["project_id"] = net_project_id
        network = models.Network.restore_from_simple_view(**network)

        try:
            network.insert()
        except ra_exceptions.ConflictRecords:
            LOG.info("Network %s already exists", network.uuid)
        else:
            LOG.info("Created network %s", network.uuid)

        # Handle subnets
        for subnet in subnets:
            ports = subnet.pop("ports", [])
            subnet_project_id = subnet.pop("project_id", net_project_id)
            subnet["project_id"] = subnet_project_id
            if startup_entities.get("domain"):
                subnet["dns_servers"] = [startup_entities["core_ip"]]
            subnet = models.Subnet.restore_from_simple_view(**subnet)
            subnet.network = network.uuid
            try:
                subnet.insert()
            except ra_exceptions.ConflictRecords:
                LOG.info("Subnet %s already exists", subnet.uuid)
            else:
                LOG.info("Created subnet %s", subnet.uuid)

            # Handle ports
            for port in ports:
                port_project_id = port.pop("project_id", subnet_project_id)
                port["project_id"] = port_project_id
                port["subnet"] = str(subnet.uuid)
                port = models.Port.restore_from_simple_view(**port)
                try:
                    port.insert()
                except ra_exceptions.ConflictRecords:
                    LOG.info("Port %s already exists", port.uuid)
                else:
                    LOG.info("Created port %s", port.uuid)

    # Handle pools
    for pool in startup_entities.get("machine_pools", []):
        pool = models.MachinePool.restore_from_simple_view(**pool)
        try:
            pool.insert()
        except ra_exceptions.ConflictRecords:
            LOG.info("Machine pool %s already exists", pool.uuid)
        else:
            LOG.info("Created machine pool %s", pool.uuid)


def _install_core_manifest():
    with open(CONF.manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    auth = http_client.CoreIamAuthenticator(
        base_url=CONF.core_endpoint,
        username=CONF.core_user,
        password=CONF.core_password,
    )
    client = http_client.CollectionBaseClient(
        base_url=CONF.core_endpoint,
        auth=auth,
    )

    manifest = elements.add_manifest(client, manifest)
    elements.install_manifest(client, manifest["uuid"])


def main() -> None:
    # Parse config
    config.parse(sys.argv[1:])

    retry_on_error = CONF.retry_on_error
    engines.engine_factory.configure_postgresql_factory(CONF)

    while True:
        try:
            LOG.info("GC Bootstrap script")
            _apply_startup_db()
            _install_core_manifest()
            return
        except Exception:
            LOG.exception("Unable to perform bootstrap, retrying...")
            if not retry_on_error:
                return

        time.sleep(2.0)


if __name__ == "__main__":
    main()
