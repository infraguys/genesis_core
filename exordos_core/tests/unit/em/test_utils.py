# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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
import uuid as sys_uuid

from exordos_core.elements.dm.utils import (
    get_element_uuid,
    get_project_id,
    parse_variable,
    Parsed,
)


def test_get_element_uuid():
    # Given
    element_name = "test_element"
    element_version = "1.0.0"

    # When
    result = get_element_uuid(element_name, element_version)

    # Then
    assert isinstance(result, sys_uuid.UUID)
    assert str(result).startswith("12345678")


def test_get_element_uuid_consistency():
    # Given
    element_name = "test_element"
    element_version = "1.0.0"

    # When
    result1 = get_element_uuid(element_name, element_version)
    result2 = get_element_uuid(element_name, element_version)

    # Then
    assert result1 == result2


def test_get_element_uuid_different_params():
    # Given
    element_name1 = "test_element_1"
    element_version1 = "1.0.0"
    element_name2 = "test_element_2"
    element_version2 = "1.0.0"

    # When
    result1 = get_element_uuid(element_name1, element_version1)
    result2 = get_element_uuid(element_name2, element_version2)

    # Then
    assert result1 != result2


def test_get_element_uuid_with_special_chars():
    # Given
    element_name = "test-element_with.special-chars"
    element_version = "1.0.0"

    # When
    result = get_element_uuid(element_name, element_version)

    # Then
    assert isinstance(result, sys_uuid.UUID)
    assert str(result).startswith("12345678")


def test_get_project_id():
    # When
    result = get_project_id()

    # Then
    assert isinstance(result, sys_uuid.UUID)
    assert str(result) == "12345678-0000-0000-0000-000000000000"


def test_get_project_id_consistency():
    # When
    result1 = get_project_id()
    result2 = get_project_id()

    # Then
    assert result1 == result2


@pytest.mark.parametrize(
    "input_str,required_result",
    [
        # Resource Type
        [
            "$core.configs",
            Parsed(
                input_string="$core.configs",
                element_name="core",
                is_resource_type=True,
                resource_paths=["configs"],
            ),
        ],
        [
            "$core.vs.vars",
            Parsed(
                input_string="$core.vs.vars",
                element_name="core",
                is_resource_type=True,
                resource_paths=["vs", "vars"],
            ),
        ],
        [
            "$core.vs.ps.cs",
            Parsed(
                input_string="$core.vs.ps.cs",
                element_name="core",
                is_resource_type=True,
                resource_paths=["vs", "ps", "cs"],
            ),
        ],
        [
            "$core.vs.vars.default_replicas:",
            Parsed(
                input_string="$core.vs.vars.default_replicas:",
                element_name="core",
                is_resource_type=True,
                resource_paths=["vs", "vars", "default_replicas:"],
            ),
        ],
        # Vars
        [
            "$core.vs.vars.$default_replicas:value",
            Parsed(
                input_string="$core.vs.vars.$default_replicas:value",
                element_name="core",
                is_variable=True,
                is_resource=True,
                resource_paths=["vs", "vars"],
                resource_name="default_replicas",
                value="value",
                resource_type="$core.vs.vars",
            ),
        ],
        [
            "$core.dns.domains.$local_domain:uuid",
            Parsed(
                input_string="$core.dns.domains.$local_domain:uuid",
                element_name="core",
                is_variable=True,
                is_resource=True,
                resource_paths=["dns", "domains"],
                resource_name="local_domain",
                value="uuid",
                resource_type="$core.dns.domains",
            ),
        ],
        # # Imports, Exports
        [
            "$core.vs.vars.$default_ram",
            Parsed(
                input_string="$core.vs.vars.$default_ram",
                element_name="core",
                is_resource=True,
                resource_paths=["vs", "vars"],
                resource_name="default_ram",
                resource_type="$core.vs.vars",
            ),
        ],
        # Invalid
        [
            "$core.vs.vars.default_replicas:value",
            Parsed(
                valid=False,
                error="Not found resource",
                input_string="$core.vs.vars.default_replicas:value",
            ),
        ],
        [
            "core.compute.sets",
            Parsed(
                valid=False, error="Invalid format", input_string="core.compute.sets"
            ),
        ],
        [
            "not_a_variable",
            Parsed(valid=False, error="Invalid format", input_string="not_a_variable"),
        ],
        ["", Parsed(valid=False, error="Invalid format", input_string="")],
        ["$", Parsed(valid=False, error="Invalid format", input_string="$")],
        ["$core", Parsed(valid=False, error="Invalid format", input_string="$core")],
    ],
)
def test_parse_variable(input_str: str, required_result):
    result = parse_variable(input_str)

    assert result == required_result
