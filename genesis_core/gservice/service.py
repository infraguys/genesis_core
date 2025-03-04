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

import logging

from gcl_looper.services import basic

from genesis_core.node.scheduler import service as n_scheduler_service
from genesis_core.node.machine import service as n_machine_service


LOG = logging.getLogger(__name__)


class GeneralService(basic.BasicService):

    def __init__(self, iter_min_period=1, iter_pause=0.1):
        super().__init__(iter_min_period, iter_pause)

        # The simplest way to enable the nested services
        # It will be reworked in the future
        n_scheduler = n_scheduler_service.NodeSchedulerService(
            iter_min_period=1, iter_pause=0.1
        )
        n_machine = n_machine_service.MachineAgentService(
            iter_min_period=1, iter_pause=0.1
        )

        self._services = [n_scheduler, n_machine]

    def _setup(self):
        LOG.info("Setup all services")
        for service in self._services:
            service._setup()

    def _iteration(self):
        # Iterate all services
        for service in self._services:
            try:
                service._iteration()
            except Exception:
                LOG.exception("Error in service %s", service)
