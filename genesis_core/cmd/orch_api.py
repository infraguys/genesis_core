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

from gcl_looper.services import bjoern_service
from oslo_config import cfg
from restalchemy.common import config_opts as ra_config_opts
from restalchemy.storage.sql import engines

from genesis_core.orch_api.api import app
from genesis_core.common import config
from genesis_core.common import log as infra_log


api_cli_opts = [
    cfg.StrOpt(
        "bind-host",
        default="127.0.0.1",
        help="The host IP to bind to",
    ),
    cfg.IntOpt(
        "bind-port",
        default=11011,
        help="The port to bind to",
    ),
    cfg.IntOpt(
        "workers",
        default=1,
        help="How many http servers should be started",
    ),
]


DOMAIN = "orch_api"

CONF = cfg.CONF
CONF.register_cli_opts(api_cli_opts, DOMAIN)
ra_config_opts.register_posgresql_db_opts(CONF)


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_postgresql_factory(CONF)

    log.info(
        "Start service on %s:%s",
        CONF[DOMAIN].bind_host,
        CONF[DOMAIN].bind_port,
    )

    service = bjoern_service.BjoernService(
        wsgi_app=app.build_wsgi_application(),
        host=CONF[DOMAIN].bind_host,
        port=CONF[DOMAIN].bind_port,
        bjoern_kwargs=dict(reuse_port=True),
    )

    service.start()

    log.info("Bye!!!")


if __name__ == "__main__":
    main()
