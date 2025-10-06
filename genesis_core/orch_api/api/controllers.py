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

from oslo_config import cfg
from restalchemy.api import controllers
from restalchemy.api import resources
from restalchemy.storage import exceptions as ra_storage_exceptions

from genesis_core.common import constants as c
from genesis_core.compute import constants as nc
from genesis_core.orch_api.dm import models
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


class NetBootController(controllers.BaseResourceControllerPaginated):
    """Controller for /v1/boots/ endpoint"""

    __resource__ = resources.ResourceByRAModel(
        model_class=models.MachineNetboot,
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
            netboot = models.MachineNetboot(
                uuid=uuid,
                cores=0,
                ram=0,
                boot=nc.BootAlternative.network.value,
                project_id=c.SERVICE_PROJECT_ID,
            )

        # Set netboot configuration
        netboot.set_netboot_params(
            CONF[DOMAIN].gc_host,
            CONF[DOMAIN].gc_orch_api,
            CONF[DOMAIN].gc_status_api,
            CONF[DOMAIN].kernel,
            CONF[DOMAIN].initrd,
        )

        return netboot, 200, {"Content-Type": "application/octet-stream"}
