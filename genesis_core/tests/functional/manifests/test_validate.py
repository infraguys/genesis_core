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

import pytest
import requests
import yaml

from genesis_core.elements.dm.validate import (
    validate_manifest,
    dump_full_manifest_schema,
)

REPO_URL = "https://repository.genesis-core.tech/genesis-elements"


class TestSpec:
    @pytest.mark.parametrize(
        "element",
        [
            "communal_pg_cluster",
            "core",
            "dbaas",
            "core-node-set-example",
            "core-service-example",
            "genesis_notification",
        ],
    )
    def test_validate_manifests(
        self, element, base_manifest_schema, full_manifest_schema
    ):
        resp = requests.get(f"{REPO_URL}/{element}/latest/manifests/{element}.yaml")
        if resp.status_code == 404:
            pytest.skip(f"latest version for {element} is not available")
        assert resp.status_code == 200
        manifest = yaml.safe_load(resp.text)
        validate_manifest(manifest, base_manifest_schema)
        validate_manifest(manifest, full_manifest_schema)

    @pytest.mark.skip(reason="for manual running")
    def test_build_full_schema(self, base_manifest_schema, user_api_spec):
        path_schema = []
        for path, path_obj in user_api_spec["paths"].items():
            path_parts = path.split("/")
            if len(path_parts) > 5:
                continue
            post_path = path_obj.get("post")
            if post_path:
                operation_id = post_path.get("operationId")
                if operation_id and operation_id.startswith("Create_v1"):
                    schema_ref = post_path["requestBody"]["content"][
                        "application/json"
                    ]["schema"]
                    model_name = schema_ref["$ref"].split("/")[-1]
                    api_part_1 = path_parts[2]
                    api_part_2 = path_parts[3]
                    model = user_api_spec["components"]["schemas"][model_name]
                    resource = f"$core.{api_part_1}.{api_part_2}"
                    path_schema.append(
                        {
                            "path": path,
                            "schema": schema_ref,
                            "resource": resource,
                            "model_name": model_name,
                            "model": model,
                        }
                    )
                    base_manifest_schema["components"]["schemas"][model_name] = model
                    base_manifest_schema["properties"]["resources"]["properties"][
                        resource
                    ] = {
                        "type": "object",
                        "additionalProperties": schema_ref,
                    }

        assert path_schema
        dump_full_manifest_schema(base_manifest_schema)
