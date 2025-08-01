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
from gcl_sdk.events.services import senders

from genesis_core.elements.services import builders as em_builders
from genesis_core.node.scheduler.driver.filters import available
from genesis_core.node.scheduler.driver.weighter import relative
from genesis_core.node.scheduler import service as n_scheduler_service
from genesis_core.node.builder import service as n_builder_service
from genesis_core.node.machine import service as n_machine_service
from genesis_core.network import service as n_network_service
from genesis_core.config import service as config_service
from genesis_core.secret import service as secret_service
from genesis_core.janitor import service as janitor_service


LOG = logging.getLogger(__name__)


class GeneralService(basic.BasicService):

    def __init__(self, iter_min_period=1, iter_pause=0.1):
        super().__init__(iter_min_period, iter_pause)

        # TODO(akremenetsky): Form a pipliene from the configuration
        # and entry points
        pool_filters = [
            available.CoresRamAvailableFilter(),
        ]
        pool_weighters = [
            relative.RelativeCoreRamWeighter(),
        ]
        machine_filters = [
            available.HWCoresRamAvailableFilter(),
        ]
        machine_weighters = [
            relative.SimpleMachineWeighter(),
        ]

        # The simplest way to enable the nested services
        # It will be reworked in the future
        n_scheduler = n_scheduler_service.NodeSchedulerService(
            pool_filters=pool_filters,
            pool_weighters=pool_weighters,
            machine_filters=machine_filters,
            machine_weighters=machine_weighters,
            iter_min_period=1,
            iter_pause=0.1,
        )
        n_network = n_network_service.NetworkService(
            iter_min_period=1, iter_pause=0.1
        )
        n_builder = n_builder_service.NodeBuilderService(
            iter_min_period=1, iter_pause=0.1
        )
        n_machine = n_machine_service.MachineAgentService(
            iter_min_period=1, iter_pause=0.1
        )
        cfg_service = config_service.ConfigServiceBuilder()
        secret_svc = secret_service.SecretServiceBuilder()
        event_sender = senders.EventSenderService.build_from_config()
        em_builder = em_builders.ElementManagerBuilder(
            iter_min_period=1, iter_pause=0.1
        )
        janitor = janitor_service.ExpiredEmailConfirmationCodeJanitorService(
            iter_min_period=60 * 60,
            iter_pause=0,
        )

        self._services = [
            n_scheduler,
            n_network,
            n_builder,
            n_machine,
            cfg_service,
            secret_svc,
            event_sender,
            em_builder,
            janitor,
        ]

    def _setup(self):
        LOG.info("Setup all services")
        for service in self._services:
            service._setup()

    def _iteration(self):
        # Iterate all services
        for service in self._services:
            service._loop_iteration()
