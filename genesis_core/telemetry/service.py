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

import logging
from concurrent import futures

import bazooka
from bazooka import exceptions as bazooka_exc
from requests import auth as requests_auth

from gcl_looper.services import basic
from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters

from genesis_core.common import constants as c
from genesis_core.compute.dm import models as compute_models
from genesis_core.config.dm import models as config_models
from genesis_core.elements.dm import models as em_models
from genesis_core.secret.dm import models as secret_models
from genesis_core.user_api.dns.dm import models as dns_models
from genesis_core.user_api.iam.dm import models as iam_models
from genesis_core.user_api.network.dm import models as net_models
from genesis_core.user_api.security.dm import models as security_models
from genesis_core.vs.dm import models as vs_models

LOG = logging.getLogger(__name__)

TELEMETRY_TIMEOUT = 30
TELEMETRY_POOL_SIZE = 1


class TelemetryService(basic.BasicService):
    """Periodically collects and sends telemetry data to the ecosystem."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = bazooka.Client(default_timeout=TELEMETRY_TIMEOUT)
        self._executor = futures.ThreadPoolExecutor(max_workers=TELEMETRY_POOL_SIZE)
        self._pending_future = None

    def _get_variable_value(self, var_uuid):
        """Read variable value from ValuesStore by UUID."""
        variable = vs_models.Variable.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(var_uuid)}
        )
        if variable is None:
            return None
        return variable.value

    @staticmethod
    def _safe_collect(data, collector, group_name):
        """Run a collector function and log errors without raising."""
        try:
            collector(data)
        except Exception:
            LOG.exception("Failed to collect %s metrics", group_name)

    @staticmethod
    def _count_entities(data, counts):
        """Collect counts for a list of (key, model_class) pairs."""
        for key, model_class in counts:
            try:
                data[key] = model_class.objects.count()
            except Exception:
                LOG.exception("Failed to count %s", key)

    @staticmethod
    def _collect_compute_nodes(data):
        nodes = compute_models.Node.objects.get_all()
        data["nodes_count"] = len(nodes)
        data["nodes_total_cores"] = sum(n.cores for n in nodes)
        data["nodes_total_ram"] = sum(n.ram for n in nodes)

    @staticmethod
    def _collect_machine_pools(data):
        pools = compute_models.MachinePool.objects.get_all()
        data["machine_pools_count"] = len(pools)
        data["machine_pools_total_cores"] = sum(p.all_cores for p in pools)
        data["machine_pools_total_ram"] = sum(p.all_ram for p in pools)
        data["machine_pools_avail_cores"] = sum(p.avail_cores for p in pools)
        data["machine_pools_avail_ram"] = sum(p.avail_ram for p in pools)
        # Storage aggregates across all pools
        storage_capacity = 0
        storage_provisioned = 0
        storage_available_actual = 0
        for pool in pools:
            for sp in pool.storage_pools:
                storage_capacity += sp.capacity_usable
                storage_provisioned += sp.capacity_provisioned
                storage_available_actual += sp.available_actual
        data["storage_capacity"] = storage_capacity
        data["storage_provisioned"] = storage_provisioned
        data["storage_available_actual"] = storage_available_actual
        # Count by status
        status_counts = {}
        for pool in pools:
            key = "machine_pools_status_%s" % pool.status.lower()
            status_counts[key] = status_counts.get(key, 0) + 1
        data.update(status_counts)

    def _collect_telemetry(self):
        """Collect telemetry data from the system."""
        data = {}

        # Compute: nodes with resource aggregates
        self._safe_collect(data, self._collect_compute_nodes, "compute_nodes")

        # Compute: machine pools with detailed hypervisor stats
        self._safe_collect(data, self._collect_machine_pools, "machine_pools")

        # Compute: simple counts
        self._count_entities(
            data,
            [
                ("node_sets_count", compute_models.NodeSet),
                ("machines_count", compute_models.Machine),
                ("volumes_count", compute_models.Volume),
                ("interfaces_count", compute_models.Interface),
                ("placement_policies_count", compute_models.PlacementPolicy),
            ],
        )

        # Network
        self._count_entities(
            data,
            [
                ("networks_count", compute_models.Network),
                ("subnets_count", compute_models.Subnet),
                ("ports_count", compute_models.Port),
                ("lb_count", net_models.LB),
                ("lb_vhosts_count", net_models.Vhost),
                ("lb_routes_count", net_models.Route),
                ("lb_backend_pools_count", net_models.BackendPool),
            ],
        )

        # IAM
        self._count_entities(
            data,
            [
                ("iam_users_count", iam_models.User),
                ("iam_roles_count", iam_models.Role),
                ("iam_projects_count", iam_models.Project),
                ("iam_organizations_count", iam_models.Organization),
                ("iam_permissions_count", iam_models.Permission),
                ("iam_clients_count", iam_models.IamClient),
                ("iam_idp_count", iam_models.Idp),
                ("iam_role_bindings_count", iam_models.RoleBinding),
            ],
        )

        # Elements
        self._count_entities(
            data,
            [
                ("em_elements_count", em_models.Element),
                ("em_resources_count", em_models.Resource),
                ("em_manifests_count", em_models.Manifest),
            ],
        )

        # DNS
        self._count_entities(
            data,
            [
                ("dns_domains_count", dns_models.Domain),
                ("dns_records_count", dns_models.Record),
            ],
        )

        # Secrets
        self._count_entities(
            data,
            [
                ("secrets_passwords_count", secret_models.Password),
                ("secrets_certificates_count", secret_models.Certificate),
                ("secrets_ssh_keys_count", secret_models.SSHKey),
                ("secrets_rsa_keys_count", secret_models.RSAKey),
            ],
        )

        # Config
        self._count_entities(
            data,
            [
                ("configs_count", config_models.Config),
            ],
        )

        # ValuesStore
        self._count_entities(
            data,
            [
                ("vs_variables_count", vs_models.Variable),
                ("vs_profiles_count", vs_models.Profile),
            ],
        )

        # Security
        self._count_entities(
            data,
            [
                ("security_rules_count", security_models.Rule),
            ],
        )

        return data

    def _register_stand(self, endpoint, stand_uuid, stand_secret):
        """Register stand in ecosystem."""
        self._client.post(
            f"{endpoint}/v1/realms/",
            json={"uuid": stand_uuid, "secret": stand_secret},
            headers={"Content-Type": "application/json"},
        )
        LOG.info("Stand registered in ecosystem successfully")

    def _send_telemetry(self, endpoint, stand_uuid, stand_secret, data):
        """Send telemetry data to the ecosystem endpoint."""
        url = f"{endpoint}/v1/realms/{stand_uuid}/actions/push_telemetry/invoke"
        auth = requests_auth.HTTPBasicAuth(stand_uuid, stand_secret)

        try:
            self._client.post(
                url,
                json={"data": data},
                headers={"Content-Type": "application/json"},
                auth=auth,
            )
            LOG.debug("Telemetry sent successfully")
        except bazooka_exc.ForbiddenError:
            LOG.warning("Stand is not registered, attempting registration")
            try:
                self._register_stand(endpoint, stand_uuid, stand_secret)
                self._client.post(
                    url,
                    json={"data": data},
                    headers={"Content-Type": "application/json"},
                    auth=auth,
                )
                LOG.debug("Telemetry sent successfully after registration")
            except Exception:
                LOG.exception("Failed to register stand or send telemetry")
        except Exception:
            LOG.exception("Failed to send telemetry")

    def _check_pending_future(self):
        """Clear completed future to allow the next submission."""
        if self._pending_future is not None and self._pending_future.done():
            self._pending_future = None

    def _iteration(self):
        self._check_pending_future()

        with contexts.Context().session_manager():
            # Check if telemetry is disabled
            disable_telemetry = self._get_variable_value(c.VAR_DISABLE_TELEMETRY_UUID)
            if disable_telemetry:
                LOG.debug("Telemetry is disabled")
                return

            if self._pending_future is not None:
                LOG.debug("Previous telemetry request still pending, skipping")
                return

            # Read required variables
            ecosystem_endpoint = self._get_variable_value(c.VAR_ECOSYSTEM_ENDPOINT_UUID)
            stand_uuid = self._get_variable_value(c.VAR_STAND_UUID_UUID)
            stand_secret = self._get_variable_value(c.VAR_STAND_SECRET_UUID)

            if not all([ecosystem_endpoint, stand_uuid, stand_secret]):
                LOG.debug("Telemetry variables are not configured, skipping")
                return

            # Collect telemetry data synchronously, send asynchronously
            data = self._collect_telemetry()

        self._pending_future = self._executor.submit(
            self._send_telemetry,
            ecosystem_endpoint,
            stand_uuid,
            stand_secret,
            data,
        )
