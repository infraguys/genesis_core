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

from oslo_config import cfg

from exordos_core import version
from exordos_core.common import constants

LOG = logging.getLogger(__name__)

GLOBAL_SERVICE_NAME = constants.GLOBAL_SERVICE_NAME
_CONFIG_NOT_FOUND_MESSAGE = (
    f"Unable to find configuration file in the"
    f" default search paths (~/.{GLOBAL_SERVICE_NAME}/, ~/,"
    f" /etc/{GLOBAL_SERVICE_NAME}/, /etc/) and the '--config-file' option!"
)


def parse(args, conf: cfg.ConfigOpts | None = None):
    if not conf:
        conf = cfg.CONF

    conf(
        args=args,
        project=GLOBAL_SERVICE_NAME,
        version=f"{GLOBAL_SERVICE_NAME.capitalize()} {version.version_info}",
    )
    if not conf.config_file:
        LOG.warning(_CONFIG_NOT_FOUND_MESSAGE)
    return conf.config_file
