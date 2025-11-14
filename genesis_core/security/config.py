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

import os
from oslo_config import cfg

SECURITY_GROUP = cfg.OptGroup(
    name="security",
    title="Security verification options",
)

security_opts = [
    cfg.BoolOpt(
        "enabled",
        default=True,
        help="Enable security verification middleware",
    ),
]

FIREBASE_APP_CHECK_GROUP = cfg.OptGroup(
    name="verifiers.firebase_app_check",
    title="Firebase App Check verifier options",
)

firebase_app_check_opts = [
    cfg.StrOpt(
        "credentials_path",
        default="",
        help="Path to Firebase service account JSON file",
    ),
    cfg.ListOpt(
        "allowed_app_ids",
        default=[],
        help="List of allowed Firebase App IDs",
    ),
    cfg.StrOpt(
        "mode",
        default="enforce",
        choices=("enforce", "report-only"),
        help="Verification mode: enforce or report-only",
    ),
]

CAPTCHA_GROUP = cfg.OptGroup(
    name="verifiers.captcha",
    title="CAPTCHA verifier options",
)

captcha_opts = [
    cfg.StrOpt(
        "mode",
        default="enforce",
        choices=("enforce", "report-only"),
        help="Verification mode: enforce or report-only",
    ),
]


def register_opts(conf):
    """Register security configuration options."""
    conf.register_group(SECURITY_GROUP)
    conf.register_opts(security_opts, group=SECURITY_GROUP)

    conf.register_group(FIREBASE_APP_CHECK_GROUP)
    conf.register_opts(firebase_app_check_opts, group=FIREBASE_APP_CHECK_GROUP)

    conf.register_group(CAPTCHA_GROUP)
    conf.register_opts(captcha_opts, group=CAPTCHA_GROUP)


def get_security_config(conf) -> dict:
    """
    Get security configuration as dictionary.

    :param conf: oslo_config.CONF instance
    :return: Configuration dictionary
    """
    config = {}

    # Security group
    if conf.security.enabled:
        config["enabled"] = True

        # Firebase App Check config
        firebase_config = {}
        firebase_section = conf["verifiers.firebase_app_check"]
        if firebase_section.credentials_path:
            firebase_config["credentials_path"] = os.path.abspath(
                firebase_section.credentials_path
            )
        if firebase_section.allowed_app_ids:
            firebase_config["allowed_app_ids"] = (
                firebase_section.allowed_app_ids
            )
        firebase_config["mode"] = firebase_section.mode
        config["verifiers.firebase_app_check"] = firebase_config

        # CAPTCHA config
        captcha_config = {}
        captcha_section = conf["verifiers.captcha"]
        captcha_config["mode"] = captcha_section.mode
        config["verifiers.captcha"] = captcha_config

    return config

