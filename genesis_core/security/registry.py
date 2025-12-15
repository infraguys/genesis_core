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

# Entry point group name for verifiers
ENTRY_POINT_GROUP = "genesis_core.verifiers"
VERIFIER_CONFIG_PREFIX = "verifiers."

# Export ENTRY_POINT_GROUP for use in other modules
__all__ = ["ENTRY_POINT_GROUP", "VERIFIER_CONFIG_PREFIX"]
