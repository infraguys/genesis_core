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
import datetime
import typing as tp

import netaddr
from oslo_config import cfg
from restalchemy.api import actions
from restalchemy.api import resources
from restalchemy.api import controllers
from restalchemy.dm import filters as dm_filters
from restalchemy.storage import exceptions as ra_storage_exceptions

from genesis_core.node.dm import models
from genesis_core.node import constants as nc
from genesis_core.orch_api.dm import models as orch_models
from genesis_core.orch_api.api import packers

DOMAIN = "orch_api"
CONF = cfg.CONF


class ApiEndpointController(controllers.RoutesListController):
    """Controller for /v1/ endpoint"""

    __TARGET_PATH__ = "/v1/"


# TODO(e.frolov): should be raw route
class HealthController(controllers.Controller):
    """Controller for /v1/health/ endpoint"""

    def filter(self, filters, **kwargs):
        return "OK"


class NodesController(controllers.BaseResourceControllerPaginated):
    """Controller for /v1/nodes/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=orch_models.Node,
        process_filters=True,
        convert_underscore=False,
    )


class MachinesController(controllers.BaseResourceControllerPaginated):
    """Controller for /v1/machines/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=orch_models.Machine,
        process_filters=True,
        convert_underscore=False,
    )


class InterfacesController(controllers.BaseNestedResourceController):
    """Controller for /v1/machines/<id>/interfaces/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=orch_models.Interface,
        process_filters=True,
        convert_underscore=False,
    )

    __pr_name__ = "machine"


class NetBootController(controllers.BaseResourceControllerPaginated):
    """Controller for /v1/boots/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=orch_models.Netboot,
        process_filters=True,
        convert_underscore=False,
    )

    __packer__ = packers.IPXEPacker

    def get(self, uuid, **kwargs):
        try:
            netboot = super().get(uuid, **kwargs)
        except ra_storage_exceptions.RecordNotFound:
            # Generate a dummy netboot object for netboot
            # configuration. Network is default option
            # for such machines.
            netboot = orch_models.Netboot(
                uuid=uuid,
                boot=nc.BootAlternative.network.value,
            )

        # Set netboot configuration
        netboot.set_netboot_params(
            CONF[DOMAIN].gc_host,
            CONF[DOMAIN].gc_port,
            CONF[DOMAIN].kernel,
            CONF[DOMAIN].initrd,
        )

        return netboot, 200, {"Content-Type": "application/octet-stream"}


class CoreAgentController(controllers.BaseResourceController):
    """Controller for /v1/core_agents/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=orch_models.CoreAgent,
        process_filters=True,
        convert_underscore=False,
    )

    @actions.get
    def get_payload(
        self,
        resource: orch_models.CoreAgent,
        payload_hash: str = "",
        payload_updated_at: str | None = None,
    ):
        if payload_updated_at is not None:
            payload_updated_at = datetime.datetime.fromisoformat(
                payload_updated_at
            )

        return resource.get_payload(
            payload_updated_at=payload_updated_at,
            payload_hash=payload_hash,
        )

    @actions.post
    def register_payload(self, resource: orch_models.CoreAgent, **payload):
        # Only machine is registered so far
        machine = orch_models.Machine.from_agent_payload(payload)

        # Check if the machine is already registered
        if models.Machine.objects.get_one_or_none(
            filters={"uuid": dm_filters.EQ(str(machine.uuid))}
        ):
            resource.machine = machine
            resource.update()
            return resource.get_payload()

        # FIXME(akremenetsky): No need builder for the HW machine
        # Audo discovery procedure
        if machine.machine_type == nc.NodeType.HW:
            # FIXME(akremenetsky): The auto discovery machines use
            # the default HW pool.
            if not machine.pool:
                if default_pool := models.MachinePool.default_hw_pool():
                    machine.pool = default_pool.uuid
                else:
                    raise ValueError("Default HW pool is not configured")
            machine.build_status = nc.MachineBuildStatus.READY.value

            machine.insert()

            # Keep the interfaces
            for iface in orch_models.Interface.from_agent_payload(
                machine, payload
            ):
                iface.insert()

        resource.machine = machine
        resource.update()

        return resource.get_payload()
