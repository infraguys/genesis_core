#    Copyright 2026 Genesis Corporation.
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

"""The manifest schema has to resolve on its own.

Both shapes here arrived with restalchemy 15.3.0, which emits component
`$ref`s where 15.2.x inlined the same schemas. Neither was caught by
anything: the build died with a bare `KeyError` on one and produced a
schema full of unresolvable references on the other, and the only reader
that would have noticed is a manifest being validated in production.
"""

from exordos_core.elements.dm import utils


def _spec(paths, schemas):
    return {"paths": paths, "components": {"schemas": schemas}}


def _create_path(model_name):
    return {
        "post": {
            "operationId": "Create_v1Thing",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model_name}"}
                    }
                }
            },
        }
    }


def _base():
    return {
        "components": {"schemas": {}},
        "properties": {"resources": {"properties": {}}},
    }


def test_an_alias_create_schema_brings_what_it_points_at():
    """`Node_Create: {$ref: Node_Get}` used to travel without `Node_Get`."""
    spec = _spec(
        {"/v1/compute/nodes/": _create_path("Thing_Create")},
        {
            "Thing_Create": {"$ref": "#/components/schemas/Thing_Get"},
            "Thing_Get": {
                "type": "object",
                "properties": {"spec": {"$ref": "#/components/schemas/Thing_Spec"}},
            },
            "Thing_Spec": {"type": "object", "properties": {}},
            "Unrelated": {"type": "object"},
        },
    )
    full = utils.build_full_schema(_base(), spec)
    copied = full["components"]["schemas"]
    assert "Thing_Get" in copied, "the alias target has to come along"
    assert "Thing_Spec" in copied, "and whatever the target itself references"
    # Only the closure, not the whole component section.
    assert "Unrelated" not in copied


def test_the_built_schema_has_no_dangling_references():
    spec = _spec(
        {"/v1/compute/nodes/": _create_path("Thing_Create")},
        {
            "Thing_Create": {"$ref": "#/components/schemas/Thing_Get"},
            "Thing_Get": {
                "type": "object",
                "properties": {
                    "one_of": {"oneOf": [{"$ref": "#/components/schemas/Thing_Kind"}]}
                },
            },
            "Thing_Kind": {"type": "object"},
        },
    )
    full = utils.build_full_schema(_base(), spec)
    schemas = full["components"]["schemas"]
    unresolved = {n for n in utils.iter_schema_refs(full) if n not in schemas}
    assert not unresolved


def test_a_create_body_without_a_named_model_is_skipped_not_fatal():
    """`/v1/iam/idp/{…}/.well_known/` posts an inline `type: object`.

    Reading `$ref` off it took down the build for every other path too.
    """
    paths = {
        "/v1/iam/idp/{IdpUuid}/.well_known/": {
            "post": {
                "operationId": "Create_v1WellKnown",
                "requestBody": {
                    "content": {"application/json": {"schema": {"type": "object"}}}
                },
            }
        },
        "/v1/compute/nodes/": _create_path("Thing_Create"),
    }
    full = utils.build_full_schema(
        _base(), _spec(paths, {"Thing_Create": {"type": "object", "properties": {}}})
    )
    declarable = full["properties"]["resources"]["properties"]
    assert "$core.compute.nodes" in declarable
    assert "$core.iam.idp.well_known" not in declarable


def test_an_example_is_read_through_the_alias():
    """`search_parameter_example` reached for `properties` on the alias."""
    scheme = {
        "properties": {
            "resources": {
                "properties": {
                    "$core.compute.nodes": {
                        "additionalProperties": {
                            "$ref": "#/components/schemas/Thing_Create"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Thing_Create": {"$ref": "#/components/schemas/Thing_Get"},
                "Thing_Get": {"properties": {"name": {"example": "any_string"}}},
            }
        },
    }
    assert (
        utils.search_parameter_example(scheme, "$core.compute.nodes", "name")
        == "any_string"
    )


def test_a_reference_cycle_does_not_hang_the_resolver():
    schemas = {
        "A": {"$ref": "#/components/schemas/B"},
        "B": {"$ref": "#/components/schemas/A"},
    }
    assert utils.resolve_schema(schemas, "A") is None
