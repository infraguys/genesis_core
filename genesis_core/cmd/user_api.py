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

from gcl_iam import algorithms
from gcl_iam import constants as glc_iam_c
from gcl_looper.services import bjoern_service
from oslo_config import cfg
from restalchemy.common import config_opts as ra_config_opts
from restalchemy.storage.sql import engines

from genesis_core.user_api.api import app
from genesis_core.common import config
from genesis_core.common import constants as c
from genesis_core.common import log as infra_log
from genesis_core.common import utils
from genesis_core.user_api.iam import constants as iam_c


api_cli_opts = [
    cfg.StrOpt(
        "bind-host",
        default=c.DEFAULT_USER_API_HOST,
        help="The host IP to bind to",
    ),
    cfg.IntOpt(
        "bind-port",
        default=c.DEFAULT_USER_API_PORT,
        help="The port to bind to",
    ),
    cfg.IntOpt(
        "workers",
        default=1,
        help="How many http servers should be started",
    ),
]

iam_cli_opts = [
    cfg.StrOpt(
        "global_salt",
        default=c.DEFAULT_GLOBAL_SALT,
        help="Global salt for IAM passwords",
    ),
    cfg.StrOpt(
        "token_encryption_algorithm",
        default="HS256",
        choices=("HS256",),
        help="Token encryption algorithm",
    ),
]

iam_token_encryption_algorithms = [
    cfg.StrOpt(
        "encryption_key",
        default=c.DEFAULT_HS256_KEY,
        help="Token encryption key",
    ),
]


DOMAIN = "user_api"
DOMAIN_IAM = "iam"


CONF = cfg.CONF
CONF.register_cli_opts(api_cli_opts, DOMAIN)
CONF.register_cli_opts(iam_cli_opts, DOMAIN_IAM)
CONF.register_cli_opts(
    iam_token_encryption_algorithms,
    iam_c.DOMAIN_IAM_TOKEN_HS256,
)
ra_config_opts.register_posgresql_db_opts(CONF)


def get_token_encryption_algorithm(conf=CONF):
    tea_name = conf[DOMAIN_IAM].token_encryption_algorithm
    if tea_name == glc_iam_c.ALGORITHM_HS256:
        return algorithms.HS256(
            key=conf[iam_c.DOMAIN_IAM_TOKEN_HS256].encryption_key,
        )
    else:
        raise ValueError("Unknown token encryption algorithm: {tea_name}")


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_postgresql_factory(CONF)

    token_algorithm = get_token_encryption_algorithm(CONF)
    context_storage = utils.get_context_storage(
        global_salt=CONF[DOMAIN_IAM].global_salt,
        token_algorithm=token_algorithm,
    )

    log.info(
        "Start service on %s:%s",
        CONF[DOMAIN].bind_host,
        CONF[DOMAIN].bind_port,
    )

    service = bjoern_service.BjoernService(
        wsgi_app=app.build_wsgi_application(
            context_storage=context_storage,
            token_algorithm=token_algorithm,
        ),
        host=CONF[DOMAIN].bind_host,
        port=CONF[DOMAIN].bind_port,
        bjoern_kwargs=dict(reuse_port=True),
    )

    service.start()

    log.info("Bye!!!")


if __name__ == "__main__":
    main()
