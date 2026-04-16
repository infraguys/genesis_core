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

import dataclasses
import logging
import os
import re
import typing as tp
import uuid as sys_uuid

import openapi_schema_validator
import yaml
from jsonschema.exceptions import ValidationError

from genesis_core.common import exceptions
from genesis_core.common.utils import PROJECT_PATH

LOG = logging.getLogger(__name__)
ELEMENT_NAMESPACE = sys_uuid.UUID("f277e88a-cd58-4c33-a0c3-23a1086a53b7")
UUID_PREFIX = "12345678"
REGEXP = re.compile(r"\$(.+?)(?:\:(.+))?$")

SchemaDict = dict[str, tp.Any]
ManifestNode = dict[str, tp.Any] | list[tp.Any] | str


@dataclasses.dataclass
class Parsed:
    input_string: str
    valid: bool = True
    error: str | None = None
    resource_type: str | None = None
    element_name: str | None = None
    resource_paths: list[str] | None = None
    resource_name: str | None = None
    value: str | None = None
    is_variable: bool = False
    is_resource: bool = False
    is_resource_type: bool = False


def clear_parameters(resource_link: str) -> str:
    parts = resource_link.split(".")
    return ".".join(parts[:-1] + [parts[-1].split(":")[0]])


class ResourceLink:
    def __init__(self, link_string: str) -> None:
        super().__init__()
        self._link_string = link_string

    @property
    def location(self) -> str:
        return clear_parameters(self._link_string)

    @property
    def parameter(self) -> str:
        return self._link_string.split(".")[-1]


def get_element_uuid(element_name: str, element_version: str) -> sys_uuid.UUID:
    tmp = str(
        sys_uuid.uuid5(
            ELEMENT_NAMESPACE,
            f"{element_name}-{element_version}",
        )
    )
    return sys_uuid.UUID(f"{UUID_PREFIX}{tmp[8:]}")


def get_project_id() -> sys_uuid.UUID:
    # return sys_uuid.UUID(f"{UUID_PREFIX}{str(sys_uuid.uuid4())[8:]}")
    return sys_uuid.UUID(
        f"{UUID_PREFIX}{str('00000000-0000-0000-0000-000000000000')[8:]}"
    )


def get_required_field(data: SchemaDict, field_name: str) -> tp.Any:
    if field_name not in data:
        raise ValueError(
            f"required field '{field_name}' is missing in the provided data: {data}"
        )
    return data[field_name]


def parse_variable(var: str) -> Parsed:
    res = re.findall(REGEXP, var)

    result = Parsed(input_string=var)
    if not res or len(res[0]) == 0:
        result.valid = False
        result.error = "Invalid format"
        return result

    parts = res[0][0].split(".")

    if len(parts) <= 1:
        result.valid = False
        result.error = "Invalid format"
        return result

    value, resource_parts, resource_name, resource_type = None, None, None, None
    is_variable, is_resource, is_resource_type = False, False, False
    element_name = parts[0]

    if len(parts) == 2:
        is_resource_type = True
        resource_parts = parts[1:]
    elif len(parts) == 3:
        if parts[-1].startswith("$"):
            resource_name = parts[-1][1:]
            resource_parts = parts[1:-1]
            is_resource = True
            resource_type = f"${element_name}.{'.'.join(resource_parts)}"
        else:
            is_resource_type = True
            resource_parts = parts[1:]
    elif len(parts) > 3:
        if len(res[0]) == 2 and res[0][1]:
            value = res[0][1]

        if parts[-1].startswith("$"):
            resource_name = parts[-1][1:]
            resource_parts = parts[1:-1]
            is_resource = True
            is_variable = value is not None
            resource_type = f"${element_name}.{'.'.join(resource_parts)}"
        elif value:
            result.valid = False
            result.error = "Not found resource"
            return result
        else:
            is_resource_type = True
            resource_parts = parts[1:]

    result.element_name = element_name
    result.resource_paths = resource_parts
    result.resource_name = resource_name
    result.value = value
    result.is_variable = is_variable
    result.is_resource = is_resource
    result.is_resource_type = is_resource_type
    result.resource_type = resource_type

    return result


def walk(node: ManifestNode) -> list[Parsed]:
    variables: list[Parsed] = []
    if isinstance(node, dict):
        for value in node.values():
            variables += walk(value)
    elif isinstance(node, list):
        for item in node:
            variables += walk(item)
    else:
        re_vars = [parse_variable(str(node))]
        if re_vars:
            variables.extend(re_vars)
    return variables


def walk_replace(resource_type: str, scheme: SchemaDict, node: ManifestNode) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str):
                parsed_var = parse_variable(value)
                if parsed_var.valid and parsed_var.is_variable:
                    replacement: tp.Any = None
                    if parsed_var.resource_type == "$core.vs.variables":
                        replacement = search_parameter_example(
                            scheme, resource_type, key
                        )
                    elif (
                        parsed_var.resource_type is not None
                        and parsed_var.value is not None
                    ):
                        replacement = search_parameter_example(
                            scheme,
                            parsed_var.resource_type,
                            parsed_var.value,
                        )
                    if replacement is not None:
                        node[key] = replacement
            else:
                walk_replace(resource_type, scheme, value)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            if isinstance(item, str):
                parsed_var = parse_variable(item)
                if parsed_var.valid and parsed_var.is_variable:
                    replacement = None
                    if parsed_var.resource_type == "$core.vs.variables":
                        replacement = search_parameter_example(
                            scheme, resource_type, item
                        )
                    elif (
                        parsed_var.resource_type is not None
                        and parsed_var.value is not None
                    ):
                        replacement = search_parameter_example(
                            scheme,
                            parsed_var.resource_type,
                            parsed_var.value,
                        )
                    if replacement is not None:
                        node[index] = replacement
            else:
                walk_replace(resource_type, scheme, item)


def load_base_manifest_schema() -> SchemaDict:
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "base_spec.yaml"
        ),
        "r",
    ) as file_obj:
        return tp.cast(SchemaDict, yaml.safe_load(file_obj))


def load_full_manifest_schema() -> SchemaDict:
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "full_spec.yaml"
        ),
        "r",
    ) as file_obj:
        return tp.cast(SchemaDict, yaml.safe_load(file_obj))


def dump_full_manifest_schema(data: SchemaDict) -> None:
    with open(
        os.path.join(
            PROJECT_PATH, "genesis", "manifests", "specification", "full_spec.yaml"
        ),
        "w",
    ) as file_obj:
        yaml.safe_dump(data, file_obj)


def load_user_api_spec() -> SchemaDict:
    with open(
        os.path.join(PROJECT_PATH, "docs", "openapi", "openapi_user.yaml"),
        "r",
    ) as file_obj:
        return tp.cast(SchemaDict, yaml.safe_load(file_obj))


def validate_manifest(data: SchemaDict, schema: SchemaDict | None) -> None:
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


def build_full_schema(
    base_manifest_schema: SchemaDict,
    user_api_spec: SchemaDict,
) -> SchemaDict:
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


def search_parameter_example(
    scheme: SchemaDict,
    resource_type: str,
    parameter: str,
) -> tp.Any:
    resource_schema = scheme["properties"]["resources"]["properties"].get(resource_type)
    if not isinstance(resource_schema, dict):
        return None

    additional_properties = resource_schema.get("additionalProperties")
    if not isinstance(additional_properties, dict):
        return None

    ref = additional_properties.get("$ref")
    if not isinstance(ref, str):
        return None

    model_name = ref.split("/")[-1]
    model = scheme["components"]["schemas"].get(model_name)
    if not isinstance(model, dict):
        return None

    model_properties = model.get("properties")
    if not isinstance(model_properties, dict):
        return None

    parameter_schema = model_properties.get(parameter)
    if not isinstance(parameter_schema, dict):
        return None

    return parameter_schema.get("example")


def mutate_manifest(manifest: SchemaDict, scheme: SchemaDict) -> SchemaDict:
    for resource_type, resource in manifest["resources"].items():
        for resource_name, resource_value in resource.items():
            walk_replace(resource_type, scheme, resource_value)
    return manifest
