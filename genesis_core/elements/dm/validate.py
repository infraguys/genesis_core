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
import os
import yaml
import typing as tp

from jsonschema.exceptions import ValidationError
import openapi_schema_validator

from genesis_core.common import exceptions
from genesis_core.common.utils import PROJECT_PATH

LOG = logging.getLogger(__name__)


def load_base_manifest_schema() -> dict:
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "base_spec.yaml"
        ),
        "r",
    ) as f:
        return yaml.safe_load(f)


def load_full_manifest_schema() -> dict:
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "full_spec.yaml"
        ),
        "r",
    ) as f:
        return yaml.safe_load(f)


def dump_full_manifest_schema(data):
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "full_spec.yaml"
        ),
        "w",
    ) as f:
        yaml.safe_dump(data, f)


def load_user_api_spec() -> dict:
    with open(
        os.path.join(PROJECT_PATH, "docs", "openapi", "openapi_user.yaml"),
        "r",
    ) as f:
        return yaml.safe_load(f)


def validate_manifest(data: dict, schema: tp.Optional[dict]) -> None:
    if data and schema:
        try:
            openapi_schema_validator.validate(
                data, schema, cls=openapi_schema_validator.OAS30Validator
            )
        except ValidationError as err:
            LOG.exception("Failed to validate data %s: %s", data, err)
            raise exceptions.OpenApiValidateException(
                err=f"{err.message} in {err.json_path}"
            )
    return None


def build_full_schema(base_manifest_schema: dict, user_api_spec: dict) -> dict:
    for path, path_obj in user_api_spec["paths"].items():
        path_parts = path.split("/")
        if len(path_parts) > 5:
            continue
        post_path = path_obj.get("post")
        if post_path:
            operation_id = post_path.get("operationId")
            if operation_id and operation_id.startswith("Create_v1"):
                schema_ref = post_path["requestBody"]["content"]["application/json"][
                    "schema"
                ]
                model_name = schema_ref["$ref"].split("/")[-1]
                api_part_1 = path_parts[2]
                api_part_2 = path_parts[3]
                model = user_api_spec["components"]["schemas"][model_name]
                resource = f"$core.{api_part_1}.{api_part_2}"
                base_manifest_schema["components"]["schemas"][model_name] = model
                base_manifest_schema["properties"]["resources"]["properties"][
                    resource
                ] = {
                    "type": "object",
                    "additionalProperties": schema_ref,
                }
    return base_manifest_schema
