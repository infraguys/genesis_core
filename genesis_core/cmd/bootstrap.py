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
import time

from oslo_config import cfg

LOG = logging.getLogger(__name__)

cli_opts = [
    cfg.BoolOpt(
        "retry_on_error",
        default=True,
        help="Should the script retry on errors",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)


def main() -> None:
    cfg.CONF()
    retry_on_error = CONF.retry_on_error

    while True:
        try:
            LOG.info("GC Bootstrap script")
            return
        except Exception:
            LOG.exception("Unable to perform bootstrap, retrying...")
            if not retry_on_error:
                return

        time.sleep(2.0)


if __name__ == "__main__":
    main()
