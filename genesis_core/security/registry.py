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
import typing as tp

from genesis_core.common import utils
from genesis_core.security.interfaces import AbstractVerifier


log = logging.getLogger(__name__)

# Entry point group name for verifiers
ENTRY_POINT_GROUP = "genesys_core.verifiers"


class VerifierRegistry:
    """
    Registry for loading and managing verifier plugins.

    Loads verifiers from entry points and provides access to them by name.
    """

    def __init__(self, config: tp.Dict[str, tp.Any] = None):
        """
        Initialize VerifierRegistry.

        :param config: Configuration dictionary with verifier-specific configs
            Expected format: {
                "verifiers.firebase_app_check": {...},
                "verifiers.captcha": {...},
            }
        """
        self.config = config or {}
        self._verifiers: tp.Dict[str, AbstractVerifier] = {}
        self._load_verifiers()

    def _load_verifiers(self):
        """Load all verifiers from entry points."""
        try:
            entry_points = utils.load_group_from_entry_point(ENTRY_POINT_GROUP)
            for ep in entry_points:
                try:
                    verifier_class = ep.load()
                    verifier_name = ep.name

                    # Get config for this verifier
                    # Support both formats: "verifiers.firebase_app_check" and direct access
                    verifier_config = self.config.get(
                        f"verifiers.{verifier_name}", {}
                    )
                    if not verifier_config:
                        # Try direct access
                        verifier_config = self.config.get(verifier_name, {})

                    # Instantiate verifier
                    verifier = verifier_class(config=verifier_config)
                    self._verifiers[verifier_name] = verifier

                    log.info(
                        f"Loaded verifier '{verifier_name}' from "
                        f"{ep.value}"
                    )
                except Exception as e:
                    log.error(
                        f"Failed to load verifier '{ep.name}': {e}",
                        exc_info=True,
                    )
        except Exception as e:
            log.error(f"Failed to load verifiers from entry points: {e}")

    def get(self, name: str) -> tp.Optional[AbstractVerifier]:
        """
        Get verifier by name.

        :param name: Verifier name
        :return: Verifier instance or None if not found
        """
        return self._verifiers.get(name)

    def list(self) -> tp.List[str]:
        """
        List all loaded verifier names.

        :return: List of verifier names
        """
        return list(self._verifiers.keys())

