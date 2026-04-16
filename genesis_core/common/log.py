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
import typing as tp
from logging import config as logging_config

import yaml
from oslo_config import cfg

DEFAULT_CONFIG = {
    "version": 1,
    "formatters": {
        "aardvark": {
            "datefmt": "%Y-%m-%d,%H:%M:%S",
            "format": "%(asctime)15s.%(msecs)03d %(processName)s"
            " pid:%(process)d tid:%(thread)d %(levelname)s"
            " %(name)s:%(lineno)d %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "aardvark",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "genesis-core": {},
    },
    "root": {"level": "DEBUG", "handlers": ["console"]},
}


logging_opts = [
    cfg.StrOpt(
        "config",
        default="logging.yaml",
        help="Logging subsystem configuration YAML file",
    )
]


class ConfigNotFound(Exception):
    pass


cfg.CONF.register_cli_opts(logging_opts, "logging")


def configure() -> None:
    config = cfg.CONF.logging.config
    config_file = cfg.CONF.find_file(config)

    if config_file is None:
        config_data: dict[str, tp.Any] = DEFAULT_CONFIG
    else:
        with open(config_file) as file_obj:
            config_data = tp.cast(dict[str, tp.Any], yaml.safe_load(file_obj))

    logging_config.dictConfig(config_data)

    if config_data == DEFAULT_CONFIG:
        logging.getLogger(__name__).warning(
            "Logging configuration %s not found - using defaults", config
        )


def die(logger: logging.Logger, message: str) -> tp.NoReturn:
    logger.error(message)
    sys.exit(1)
