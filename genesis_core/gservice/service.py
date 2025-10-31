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
import uuid as sys_uuid

from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic
from gcl_sdk.events.services import senders
from gcl_sdk.agents.universal.services import agent as ua_agent_service
from gcl_sdk.agents.universal.services import scheduler as ua_scheduler_service
from gcl_sdk.agents.universal import utils as ua_utils
from gcl_sdk.agents.universal.clients.orch import db as orch_db
from gcl_sdk.agents.universal.clients.backend import db as db_back
from gcl_sdk.agents.universal.drivers import core as ua_core_drivers

from genesis_core.elements.services import builders as em_builders
from genesis_core.compute.scheduler.driver.filters import available
from genesis_core.compute.scheduler.driver.filters import affinity
from genesis_core.compute.scheduler.driver.weighter import relative
from genesis_core.compute.scheduler import service as n_scheduler_service
from genesis_core.compute.builder import service as n_builder_service
from genesis_core.compute.machine import service as n_machine_service
from genesis_core.compute.node_set.builders import service as set_builder_svc
from genesis_core.compute.dm import models as compute_models
from genesis_core.network import service as n_network_service
from genesis_core.config import service as config_service
from genesis_core.secret import service as secret_service
from genesis_core.janitor import service as janitor_service
from genesis_core.compute.node_set.dm import models as node_set_models
from genesis_core.compute import constants as nc


LOG = logging.getLogger(__name__)
NODE_SET_TF_STORAGE = (
    "/var/lib/genesis/genesis_core/node_set/target_fields.json"
)


class GeneralService(basic.BasicService):

    def __init__(self, iter_min_period=1, iter_pause=0.1):
        super().__init__(iter_min_period, iter_pause)

        # TODO(akremenetsky): Form a pipliene from the configuration
        # and entry points
        pool_filters = [
            available.CoresRamAvailableFilter(),
            affinity.DummySoftAntiAffinityFilter(),
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
        set_builder = set_builder_svc.NodeSetBuilder(
            instance_model=node_set_models.NodeSet,
            project_id=nc.NODE_SET_PROJECT,
        )

        # Infra scheduler
        infra_scheduler = ua_scheduler_service.UniversalAgentSchedulerService(
            capabilities=["set_agent_node"]
        )

        # Infra agent
        orch_client = orch_db.DatabaseOrchClient()
        agent_uuid = sys_uuid.uuid5(ua_utils.system_uuid(), "set_agent")

        spec = db_back.ModelSpec(
            kind="set_agent_node",
            model=compute_models.Node,
            filters={"project_id": dm_filters.EQ(str(nc.NODE_SET_PROJECT))},
        )
        db_core_driver = ua_core_drivers.DatabaseCapabilityDriver(
            model_specs=[spec],
            target_fields_storage_path=NODE_SET_TF_STORAGE,
        )

        caps_drivers = [
            db_core_driver,
        ]

        facts_drivers = []

        infra_agent = ua_agent_service.UniversalAgentService(
            agent_uuid=agent_uuid,
            orch_client=orch_client,
            caps_drivers=caps_drivers,
            facts_drivers=facts_drivers,
            iter_min_period=iter_min_period,
            payload_path=None,
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
            set_builder,
            infra_scheduler,
            infra_agent,
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
