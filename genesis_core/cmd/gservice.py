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

from oslo_config import cfg
from restalchemy.storage.sql import engines

from genesis_core.common import config
from genesis_core.common import log as infra_log
from genesis_core.gservice.service import GeneralService


db_opts = [
    cfg.StrOpt(
        "connection-url",
        default="postgresql://genesis_core:genesis_core@127.0.0.1:5432/genesis_core",
        help="Connection URL to db",
    ),
]


DOMAIN = "gservice"

CONF = cfg.CONF
CONF.register_opts(db_opts, "db")


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_factory(db_url=CONF.db.connection_url)

    service = GeneralService(iter_min_period=0.5)

    service.start()

    log.info("Bye!!!")


if __name__ == "__main__":
    main()
