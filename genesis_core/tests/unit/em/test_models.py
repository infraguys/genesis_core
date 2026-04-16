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

from types import SimpleNamespace

import pytest

from genesis_core.elements.dm import models

ELEMENT_LINK = "$core"
ELEMENT_LINK_WITH_SUFFIX = "$core.api_version"
RESOURCE_LINK = "$core.resources.$database"
RESOURCE_LINK_WITH_PARAMETER = "$core.resources.$database:uuid"
RESOURCE_FIELD_LINK = "$core.resources.$database.value:uuid"
ORIGINAL_ELEMENT_LINK = "$original"
RESOLVED_ELEMENT_LINK = "$resolved"
ORIGINAL_RESOURCE_LINK = "$original.resources.$database"
RESOLVED_RESOURCE_LINK = "$resolved.resources.$database"
SCHEMA_KIND_KEY = "kind"
BASE_SCHEMA_KIND = "base"
FULL_SCHEMA_KIND = "full"
MISSING_NAMESPACE = "$missing"


def _make_element(
    link: str = ELEMENT_LINK,
    original_link: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        link=link,
        original=SimpleNamespace(link=original_link or link),
    )


def _make_resource(
    element: SimpleNamespace | None = None,
    link: str = RESOURCE_LINK,
    original_link: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        element=element or _make_element(),
        link=link,
        original=SimpleNamespace(link=original_link or link),
    )


class _StubResolverEngine:
    def __init__(
        self,
        resource: SimpleNamespace | None = None,
        element: SimpleNamespace | None = None,
    ) -> None:
        self.resource = resource or _make_resource(
            link=RESOLVED_RESOURCE_LINK,
            original_link=ORIGINAL_RESOURCE_LINK,
        )
        self.element = element or _make_element(
            link=RESOLVED_ELEMENT_LINK,
            original_link=ORIGINAL_ELEMENT_LINK,
        )
        self.resource_calls: list[tuple[SimpleNamespace, str]] = []
        self.element_calls: list[str] = []

    def get_resource_by_link(
        self,
        element: SimpleNamespace,
        link: str,
    ) -> SimpleNamespace:
        self.resource_calls.append((element, link))
        return self.resource

    def get_element(self, link: str) -> SimpleNamespace:
        self.element_calls.append(link)
        return self.element


def test_link_resolver_extract_resource_link_ignores_parameter_suffix():
    result = models.LinkResolver._extract_resource_link(RESOURCE_FIELD_LINK)

    assert result == RESOURCE_LINK


def test_link_resolver_resolves_resource_and_keeps_discarded_part():
    element = _make_element()
    resolved_resource = _make_resource(
        element=element,
        link=RESOLVED_RESOURCE_LINK,
        original_link=ORIGINAL_RESOURCE_LINK,
    )
    engine = _StubResolverEngine(resource=resolved_resource)

    resolver = models.LinkResolver(
        element_engine=engine,
        element=element,
        full_link=RESOURCE_FIELD_LINK,
    )

    assert resolver.full_link == f"{RESOLVED_RESOURCE_LINK}.value:uuid"
    assert resolver.full_link_original == f"{ORIGINAL_RESOURCE_LINK}.value:uuid"
    assert engine.resource_calls == [(element, RESOURCE_LINK)]
    assert engine.element_calls == []


def test_link_resolver_resolves_element_when_link_has_no_resource_part():
    engine = _StubResolverEngine()
    element = _make_element()

    resolver = models.LinkResolver(
        element_engine=engine,
        element=element,
        full_link=ELEMENT_LINK_WITH_SUFFIX,
    )

    assert resolver.full_link == f"{RESOLVED_ELEMENT_LINK}.api_version"
    assert resolver.full_link_original == f"{ORIGINAL_ELEMENT_LINK}.api_version"
    assert engine.element_calls == [ELEMENT_LINK]
    assert engine.resource_calls == []


def test_namespace_add_resource_and_return_all_resources():
    namespace = models.Namespace(_make_element())
    resource = _make_resource()

    namespace.add_resource(resource)

    assert namespace.get_resources() == [resource]


def test_namespace_add_resource_rejects_duplicate_links():
    namespace = models.Namespace(_make_element())
    namespace.add_resource(_make_resource())

    with pytest.raises(ValueError, match="already exists"):
        namespace.add_resource(_make_resource())


def test_namespace_get_resource_by_link_ignores_parameter_suffix():
    namespace = models.Namespace(_make_element())
    resource = _make_resource()
    namespace.add_resource(resource)

    result = namespace.get_resource_by_link(RESOURCE_LINK_WITH_PARAMETER)

    assert result is resource


def test_namespace_delete_resource_removes_resource():
    namespace = models.Namespace(_make_element())
    resource = _make_resource()
    namespace.add_resource(resource)

    namespace.delete_resource(resource)

    assert namespace.get_resources() == []


def test_namespace_delete_resource_requires_existing_resource():
    namespace = models.Namespace(_make_element())

    with pytest.raises(ValueError, match="does not exist"):
        namespace.delete_resource(_make_resource())


def test_element_engine_load_schemas_caches_loaded_values(monkeypatch):
    calls = {BASE_SCHEMA_KIND: 0, FULL_SCHEMA_KIND: 0}
    base_schema = {SCHEMA_KIND_KEY: BASE_SCHEMA_KIND}
    full_schema = {SCHEMA_KIND_KEY: FULL_SCHEMA_KIND}

    def _load_base_manifest_schema() -> dict[str, str]:
        calls[BASE_SCHEMA_KIND] += 1
        return base_schema

    def _load_full_manifest_schema() -> dict[str, str]:
        calls[FULL_SCHEMA_KIND] += 1
        return full_schema

    monkeypatch.setattr(
        models.utils,
        "load_base_manifest_schema",
        _load_base_manifest_schema,
    )
    monkeypatch.setattr(
        models.utils,
        "load_full_manifest_schema",
        _load_full_manifest_schema,
    )
    engine = models.ElementEngine()

    engine.load_schemas()
    engine.load_schemas()

    assert engine.base_schema is base_schema
    assert engine.full_schema is full_schema
    assert calls == {BASE_SCHEMA_KIND: 1, FULL_SCHEMA_KIND: 1}


def test_element_engine_get_namespace_raises_custom_exception():
    engine = models.ElementEngine()

    with pytest.raises(models.NamespaceNotFound, match="was not found"):
        engine.get_namespace(MISSING_NAMESPACE)


def test_element_engine_add_element_and_get_element():
    engine = models.ElementEngine()
    element = _make_element()

    engine.add_element(element)

    assert engine.get_element(ELEMENT_LINK) is element


def test_element_engine_add_element_rejects_duplicates():
    engine = models.ElementEngine()
    engine.add_element(_make_element())

    with pytest.raises(ValueError, match="already exists"):
        engine.add_element(_make_element())


def test_element_engine_add_resource_and_collect_resources():
    engine = models.ElementEngine()
    element = _make_element()
    resource = _make_resource(element=element)
    engine.add_element(element)

    engine.add_resource(resource)

    assert engine.get_resources() == [resource]
    assert (
        engine.get_resource_by_link(element, RESOURCE_LINK_WITH_PARAMETER) is resource
    )


def test_element_engine_delete_resource_removes_it_from_namespace():
    engine = models.ElementEngine()
    element = _make_element()
    resource = _make_resource(element=element)
    engine.add_element(element)
    engine.add_resource(resource)

    engine.delete_resource(resource)

    assert engine.get_resources() == []


def test_element_engine_add_resource_export_and_get_export_resource():
    engine = models.ElementEngine()
    element = _make_element()
    resource = _make_resource(element=element)
    engine.add_element(element)
    engine.add_resource(resource)

    engine.add_resource_export(resource)

    assert (
        engine.get_export_resource(from_element=element, link=RESOURCE_LINK) is resource
    )


def test_element_engine_add_resource_export_rejects_duplicate_links():
    engine = models.ElementEngine()
    element = _make_element()
    resource = _make_resource(element=element)
    engine.add_element(element)
    engine.add_resource(resource)
    engine.add_resource_export(resource)

    with pytest.raises(ValueError, match="already exists"):
        engine.add_resource_export(resource)


def test_element_engine_delete_resource_export_removes_mapping():
    engine = models.ElementEngine()
    element = _make_element()
    resource = _make_resource(element=element)
    engine.add_element(element)
    engine.add_resource(resource)
    engine.add_resource_export(resource)

    engine.delete_resource_export(resource)

    with pytest.raises(ValueError, match="is not in export list"):
        engine.get_export_resource(from_element=element, link=RESOURCE_LINK)


def test_element_engine_get_export_resource_raises_for_missing_link():
    engine = models.ElementEngine()

    with pytest.raises(ValueError, match="is not in export list"):
        engine.get_export_resource(
            from_element=_make_element(),
            link=RESOURCE_LINK,
        )


def test_element_engine_remove_element_requires_existing_element():
    engine = models.ElementEngine()

    with pytest.raises(ValueError, match="does not exist"):
        engine.remove_element(_make_element())
