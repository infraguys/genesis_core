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

import json
import hashlib
import typing as tp


def calculate_payload_hash(
    payload: tp.Dict[str, tp.Any],
    hash_method: tp.Callable[[str], str] = hashlib.sha256,
) -> str:
    """Calculate payload hash using dedicated fields."""
    m = hash_method()
    data = {}

    # Base payload object
    if machine := payload.get("machine"):
        data = {
            "machine": {
                "image": machine["image"],
                "node": machine.get("node"),
            }
        }

    if node := payload.get("node"):
        data["node"] = {
            "cores": node["cores"],
            "ram": node["ram"],
            "node_type": node["node_type"],
            "image": node["image"],
        }

    if renders := payload.get("renders"):
        data["renders"] = renders

    if interfaces := payload.get("interfaces"):
        data["interfaces"] = [
            {
                "mac": iface["mac"],
                "ipv4": iface["ipv4"],
                "mask": iface["mask"],
            }
            for iface in interfaces
        ]
    m.update(
        json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return m.hexdigest()
