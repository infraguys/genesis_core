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
import sys

import bazooka
from oslo_config import cfg

from genesis_core.common import config
from genesis_core.agents.clients import orch
from genesis_core.common import log as infra_log
from genesis_core.agents.core.service import CoreAgentService


DOMAIN = "core_agent"


core_agent_opts = [
    cfg.StrOpt(
        "orch_endpoint",
        default="http://localhost:11011",
        help="Endpoint of Genesis Core Orch API",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(core_agent_opts, DOMAIN)


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    http_client = bazooka.Client(default_timeout=20)

    orch_api = orch.OrchAPI(
        CONF[DOMAIN].orch_endpoint,
        http_client=http_client,
    )

    service = CoreAgentService(orch_api=orch_api, iter_min_period=3)

    service.start()

    log.info("Bye!!!")


if __name__ == "__main__":
    main()
