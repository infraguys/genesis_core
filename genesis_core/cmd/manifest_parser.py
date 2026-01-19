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
from restalchemy.common import config_opts as ra_config_opts

from genesis_core.common import config
from genesis_core.common import log as infra_log
from genesis_core.elements.dm import models

cmd_opts = [
    cfg.StrOpt(
        "manifest-path",
        required=True,
        help="Path to the manifest file",
    ),
]


CONF = cfg.CONF
ra_config_opts.register_posgresql_db_opts(CONF)
CONF.register_cli_opts(cmd_opts)


def main() -> None:
    # Parse config
    config.parse(sys.argv[1:])

    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_postgresql_factory(CONF)

    element_engine = models.element_engine
    element_engine.load_element_from_manifest_file(CONF.manifest_path)
    print(element_engine._namespaces)
    print(
        "Manifest:",
        element_engine._namespaces["$core"]
        ._namespace_resources["$core.v1.iam.projects.$compute"]
        .manifest_state,
    )
    print(
        "Render:",
        element_engine._namespaces["$core"]
        ._namespace_resources["$core.v1.iam.projects.$compute"]
        .render_target_state(),
    )

    log.debug("GoodBye!")


if __name__ == "__main__":
    main()
