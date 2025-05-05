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

from gcl_sdk.events import opts as sdk_opts
from oslo_config import cfg
from restalchemy.common import config_opts as ra_config_opts
from restalchemy.storage.sql import engines

from genesis_core.common import config
from genesis_core.common import log as infra_log
from genesis_core.gservice.service import GeneralService


DOMAIN = "gservice"

CONF = cfg.CONF
ra_config_opts.register_posgresql_db_opts(CONF)
sdk_opts.register_event_opts(CONF)


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_postgresql_factory(CONF)

    service = GeneralService(iter_min_period=3)

    service.start()

    log.info("Bye!!!")


if __name__ == "__main__":
    main()
