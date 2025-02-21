import logging
import sys

from gcl_looper.services import bjoern_service
from oslo_config import cfg
from restalchemy.storage.sql import engines

from genesis_core.user_api import app
from genesis_core.common import config
from genesis_core.common import log as infra_log


api_cli_opts = [
    cfg.StrOpt(
        "bind-host", default="127.0.0.1", help="The host IP to bind to"
    ),
    cfg.IntOpt("bind-port", default=11010, help="The port to bind to"),
    cfg.IntOpt(
        "workers", default=1, help="How many http servers should be started"
    ),
]

db_opts = [
    cfg.StrOpt(
        "connection-url",
        default="postgresql://genesis_core:genesis_core@127.0.0.1:5432/genesis_core",
        help="Connection URL to db",
    ),
]


DOMAIN = "user_api"

CONF = cfg.CONF
CONF.register_cli_opts(api_cli_opts, DOMAIN)
CONF.register_opts(db_opts, "db")


def main():
    # Parse config
    config.parse(sys.argv[1:])

    # Configure logging
    infra_log.configure()
    log = logging.getLogger(__name__)

    engines.engine_factory.configure_factory(db_url=CONF.db.connection_url)

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
