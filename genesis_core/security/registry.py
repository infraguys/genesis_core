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
from typing import Any

from genesis_core.common import utils
from genesis_core.security.interfaces import AbstractVerifier


log = logging.getLogger(__name__)

# Entry point group name for verifiers
ENTRY_POINT_GROUP = "genesys_core.verifiers"


class VerifierRegistry:
    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self._verifiers: dict[str, AbstractVerifier] = {}
        self._load_verifiers()

    def _load_verifiers(self):
        try:
            entry_points = utils.load_group_from_entry_point(ENTRY_POINT_GROUP)
            for ep in entry_points:
                try:
                    verifier_class = ep.load()
                    verifier_config = self.config.get(f"verifiers.{ep.name}", {})

                    self._verifiers[ep.name] = verifier_class(config=verifier_config)
                    log.info("Loaded verifier %s from %s", ep.name, ep.module_name)
                except Exception:
                    log.exception("Failed to load verifier %s", ep.name)
        except Exception:
            log.exception("Failed to load verifiers from entry points")

    def get(self, name: str) -> AbstractVerifier | None:
        return self._verifiers.get(name)

    def list(self) -> list[str]:
        return list(self._verifiers.keys())

