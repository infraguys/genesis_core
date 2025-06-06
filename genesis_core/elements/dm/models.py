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
import enum
import yaml
import uuid as sys_uuid

from gcl_sdk.agents.universal.dm import models as sdk_models
from gcl_sdk.agents.universal import utils as sdk_utils
from restalchemy.dm import filters as ra_filters
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types as ra_types
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import engines

from genesis_core.elements.dm import utils


LOG = logging.getLogger(__name__)


class Status(enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ACTIVE = "ACTIVE"


class AlwaysActiveStatus(enum.Enum):
    ACTIVE = "ACTIVE"


class InstallTypes(enum.Enum):
    MANUAL = "MANUAL"
    AUTO_AS_DEPENDENCY = "AUTO_AS_DEPENDENCY"


class Manifest(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "em_manifests"

    STATUS = AlwaysActiveStatus

    status = properties.property(
        ra_types.Enum([s.value for s in Status]),
        default=STATUS.ACTIVE.value,
    )
    version = properties.property(
        ra_types.String(min_length=5, max_length=64),
        read_only=True,
        required=True,
    )
    schema_version = properties.property(
        ra_types.Integer(min_value=1, max_value=1),
        read_only=True,
        default=1,
    )
    project_id = properties.property(
        ra_types.UUID(),
        read_only=True,
        default=sys_uuid.UUID("12345678-cd58-4c33-a0c3-23a1086a53b7"),
    )
    requirements = properties.property(
        ra_types.Dict(),
        read_only=True,
        mutable=True,
        default=dict,
    )
    resources = properties.property(
        ra_types.Dict(),
        read_only=True,
        mutable=True,
        default=dict,
    )

    def install(self):
        element = Element(
            uuid=utils.get_element_uuid(self.name, self.version),
            name=self.name,
            version=self.version,
            description=self.description,
            project_id=utils.get_project_id(),
        )
        element.insert()
        # prepare resources:
        for resource_link_prefix, resource in self.resources.items():
            for resource_name, resource_value in resource.items():
                uuid = sys_uuid.UUID(
                    resource_value.get("uuid", str(sys_uuid.uuid4()))
                )
                resource = Resource(
                    uuid=uuid,
                    name=resource_name,
                    element=element,
                    resource_link_prefix=resource_link_prefix,
                    value=resource_value,
                )
                resource.insert()
        return self

    def uninstall(self):
        elements = Element.objects.get_all(
            filters={
                "uuid": ra_filters.EQ(
                    utils.get_element_uuid(self.name, self.version)
                ),
            }
        )
        for element in elements:
            element.delete()
        return self


class Element(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
    models.ModelWithTimestamp,
    models.CustomPropertiesMixin,
    orm.SQLStorableMixin,
):
    __tablename__ = "em_elements"
    __custom_properties__ = {
        "link": ra_types.String(),
    }

    STATUSES = Status
    INSTALL_TYPES = InstallTypes

    status = properties.property(
        ra_types.Enum([s.value for s in STATUSES]),
        default=STATUSES.NEW.value,
    )

    version = properties.property(
        ra_types.String(min_length=5, max_length=64),
        required=True,
    )

    install_type = properties.property(
        ra_types.Enum([s.value for s in INSTALL_TYPES]),
        default=INSTALL_TYPES.MANUAL.value,
    )

    @property
    def link(self):
        return f"${self.name}"

    # def get_requirements(self):
    #     return self._requirements

    # def _add_requirement_to_list(self, requirement, list_of_requirements):
    #     for req in list_of_requirements:
    #         if req.name == requirement.name:
    #             raise exceptions.ConflictRequirement(requirement=requirement)
    #     list_of_requirements.append(requirement)
    #     return list_of_requirements

    # def add_requirement(self, requirement):
    #     self._requirements = self._add_requirement_to_list(
    #         requirement,
    #         self._requirements,
    #     )

    # def add_requirements(self, requirements):
    #     copy_requirements = self._requirements
    #     for req in requirements:
    #         copy_requirements = self._add_requirement_to_list(
    #             req,
    #             copy_requirements,
    #         )
    #     self._requirements = copy_requirements

    # def get_resources(self):
    #     return self._resources

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._requirements = []


class ElementIncorrectStatusesView(
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    __tablename__ = "em_incorrect_statuses_view"

    STATUS = Status

    name = properties.property(
        ra_types.String(min_length=1, max_length=255),
        read_only=True,
    )
    api_status = properties.property(
        ra_types.Enum([s.value for s in Status]),
        read_only=True,
    )
    actual_status = properties.property(
        ra_types.Enum([s.value for s in Status]),
        read_only=True,
    )

    def actualize_api_status(self):
        engine = engines.engine_factory.get_engine()
        with engine.session_manager() as s:
            s.execute(
                """
                UPDATE em_elements
                SET status = %s
                WHERE uuid = %s;
                """,
                [self.actual_status, self.uuid],
            )


class Requirement(
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    __tablename__ = "em_requirements"

    element = relationships.relationship(
        Element,
        prefetch=True,
        required=True,
    )
    name = properties.property(
        ra_types.String(min_length=1, max_length=64),
        required=True,
    )
    from_version = properties.property(
        ra_types.String(min_length=5, max_length=64),
        required=True,
    )
    to_version = properties.property(
        ra_types.String(min_length=5, max_length=64),
        required=True,
    )


class Resource(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    models.CustomPropertiesMixin,
    orm.SQLStorableMixin,
):
    __tablename__ = "em_resources"
    __custom_properties__ = {
        # "project_id": ra_types.UUID(),
        # "target_state": ra_types.Dict(),
        # "target_hash": ra_types.String(min_length=32, max_length=32),
        # "actual_hash": ra_types.String(min_length=32, max_length=32),
        "link": ra_types.String(min_length=2, max_length=256),
        "kind": ra_types.String(min_length=2, max_length=256),
    }
    __allowed_methods_from_manifest__ = [
        "get_uri",
    ]

    element = relationships.relationship(
        Element,
        prefetch=True,
        required=True,
    )
    name = properties.property(
        ra_types.String(min_length=1, max_length=255),
        read_only=True,
    )
    status = properties.property(
        ra_types.Enum(Status),
        default=Status.NEW.value,
    )
    resource_link_prefix = properties.property(
        ra_types.String(min_length=1, max_length=256),
        required=True,
    )
    value = properties.property(
        ra_types.Dict(),
        required=True,
        mutable=True,
    )
    target_resource = relationships.relationship(
        sdk_models.TargetResource,
        default=None,
        prefetch=True,
    )
    actual_resource = relationships.relationship(
        sdk_models.Resource,
        default=None,
        prefetch=True,
    )
    full_hash = properties.property(
        ra_types.String(max_length=256),
        default="",
    )

    def get_uri(self):
        parts = self.link.split(".")
        return f"/{"/".join(parts[1:-1])}/{self.uuid}"

    def get_parameter_value(self, parameter):
        parts = parameter.split(":")
        resource_name = parts[0][1:]
        if resource_name != self.name:
            raise ValueError(
                f"Resource name `{resource_name}` does not match the"
                f" current resource name `{self.name}`"
            )
        resource_parameter_path = parts[1:]
        if len(resource_parameter_path) == 0:
            return self.actual_resource.value
        elif len(resource_parameter_path) == 1:
            if resource_parameter_path[0][-2:] == "()":
                func_name = resource_parameter_path[0][:-2]
                if func_name in self.__allowed_methods_from_manifest__:
                    func = getattr(self, func_name)
                    return func()

        result_value = self.get_actual_state_safe()
        for part in resource_parameter_path:
            result_value = result_value[part]
        return result_value

    def get_actual_state_safe(self):
        if self.actual_resource is None:
            return self.render_target_state()
        return self.actual_resource.value

    def render_target_state(self, engine=None):

        engine = engine or element_engine

        def render_value(value):
            if value.startswith("$"):
                link = utils.ResourceLink(value)
                try:
                    resource = engine.get_resource_by_link(
                        element=self.element,
                        link=link.location,
                    )
                    return resource.get_parameter_value(
                        parameter=link.parameter,
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Can't render value `{value}` for resource"
                        f" `{repr(self)}` by reason: {e}"
                    )
            return value

        def recursive_render(data):
            if isinstance(data, dict):
                result = {}
                for key, value in data.items():
                    if isinstance(
                        value,
                        (
                            dict,
                            list,
                        ),
                    ):
                        value = recursive_render(value)
                        result[key] = value
                    elif isinstance(value, str):
                        result[key] = render_value(value)
                    else:
                        result[key] = value
            elif isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(
                        item,
                        (
                            dict,
                            list,
                        ),
                    ):
                        item = recursive_render(item)
                        result.append(item)
                    elif isinstance(item, str):
                        result.append(render_value(item))
                    else:
                        result.append(item)
            else:
                result = data
            return result

        return recursive_render(self.value)

    @property
    def link(self):
        return f"{self.resource_link_prefix}.${self.name}"

    @property
    def kind(self):
        parts = [p for p in self.resource_link_prefix.split(".")[1:]]
        return f"em_{self.element.name}_{'_'.join(parts)}"

    def calculate_full_hash(self):
        if self.actual_resource is not None:
            self.full_hash = self.actual_resource.full_hash
        else:
            target_state = self.render_target_state()
            self.full_hash = sdk_utils.calculate_hash(target_state)
        self.update()
        return self.full_hash

    def actualize(self):
        target_state = self.render_target_state()
        hash = sdk_utils.calculate_hash(target_state)
        self.calculate_full_hash()
        if self.target_resource is None:
            target_resource = sdk_models.TargetResource(
                uuid=self.uuid,
                kind=self.kind,
                value=target_state,
                hash=hash,
                full_hash=self.full_hash,
                tracked_at=self.updated_at,
            )
            target_resource.insert()
            self.target_resource = target_resource
            self.update()
            LOG.debug("Target resource %r has been created.", target_resource)
        elif self.target_resource.hash != hash:
            self.target_resource.value = target_state
            self.target_resource.calculate_hash()
            self.target_resource.full_hash = self.full_hash
            self.target_resource.tracked_at = self.updated_at
            self.target_resource.update()
            LOG.debug(
                "Target resource %r has been updated.",
                self.target_resource,
            )
        else:
            LOG.debug(
                "Target resource %r is actual state.",
                self.target_resource,
            )

    def delete(self, session=None):
        for ts in sdk_models.TargetResource.objects.get_all(
            filters={"uuid": ra_filters.EQ(self.uuid)}
        ):
            ts.delete(session=session)
        super().delete(session=session)


class OutdatedResources(models.ModelWithUUID, orm.SQLStorableMixin):

    __tablename__ = "em_outdated_resources_view"

    em_resource = relationships.relationship(
        Resource,
        default=None,
        prefetch=True,
    )
    target_resource = relationships.relationship(
        sdk_models.TargetResource,
        default=None,
        prefetch=True,
    )


class Namespace:

    def __init__(self, element):
        super().__init__()
        self._element = element
        # NOTE(efrolov): map of resources by link string
        self._namespace_resources = {}

    def add_resource(self, resource):
        if resource.link in self._namespace_resources:
            raise ValueError(
                f"Resource with link string '{resource.link}' already exists."
            )
        self._namespace_resources[resource.link] = resource

    def get_resources(self):
        return list(self._namespace_resources.values())

    def delete_resource(self, resource):
        if resource.link not in self._namespace_resources:
            raise ValueError(
                f"Resource with link string '{resource.link}' does not exist."
            )
        del self._namespace_resources[resource.link]

    def get_resource_by_link(self, link):
        clear_link = utils.clear_parameters(link)
        if clear_link not in self._namespace_resources:
            raise ValueError(
                f"Resource with link string '{clear_link}' does not exist."
            )
        return self._namespace_resources[clear_link]


class BaseManifestParser:
    SCHEMA_VERSION = 0

    def __init__(self, manifest):
        super().__init__()
        self._manifest = manifest

    def load_element_from_manifest(self, manifest):
        raise NotImplementedError("Subclasses must implement this method.")


class ManifestParserV1(BaseManifestParser):
    SCHEMA_VERSION = 1

    def load_element(
        self,
    ):
        name = utils.get_required_field(self._manifest, "Name")
        version = utils.get_required_field(self._manifest, "Version")
        description = self._manifest.get("Description", "")
        uuid = utils.get_element_uuid(name, version)
        project_id = utils.get_project_id()
        element = Element(
            uuid=uuid,
            name=name,
            version=version,
            description=description,
            project_id=project_id,
        )
        return element

    def load_resources(self, element):
        result = []
        data = self._manifest.get("Resources", {})
        for resource_link_prefix, resource_data in data.items():
            for resource_name, resource_data in resource_data.items():
                resource_uuid = resource_data.get(
                    "uuid", str(sys_uuid.uuid4())
                )
                project_id = resource_data.get(
                    "project_id", str(element.project_id)
                )
                raw_properties = resource_data.copy()
                raw_properties.update(
                    {
                        "uuid": resource_uuid,
                        "project_id": project_id,
                    }
                )
                resource = Resource(
                    uuid=sys_uuid.UUID(resource_uuid),
                    element=element,
                    resource_link_prefix=resource_link_prefix,
                    name=resource_name,
                    manifest_state=raw_properties,
                )
                result.append(resource)
        return result


class ElementEngine:

    MANIFEST_PARSER_MAP = {
        ManifestParserV1.SCHEMA_VERSION: ManifestParserV1,
    }

    def __init__(self):
        super().__init__()
        self._namespaces = {}

    def load_element_from_manifest(self, manifest):
        schema_version = utils.get_required_field(manifest, "SchemaVersion")
        manifest_parser_class = self.MANIFEST_PARSER_MAP.get(
            schema_version,
            BaseManifestParser,
        )
        manifest_parser = manifest_parser_class(manifest=manifest)
        element = manifest_parser.load_element()
        self.add_element(element)
        for resource in manifest_parser.load_resources(element):
            self.add_resource(resource)

    def load_from_database(self):
        self._namespaces = {}
        for element in Element.objects.get_all():
            self.add_element(element)

        for resource in Resource.objects.get_all():
            self.add_resource(resource)

    def load_element_from_manifest_file(self, manifest_file_path):
        with open(manifest_file_path, "r") as file:
            manifest = yaml.safe_load(file)
        self.load_element_from_manifest(manifest)

    def add_resource(self, resource):
        element = resource.element
        if element.link not in self._namespaces:
            ValueError(
                f"The element '{element}' is unknown. Please add the element"
                " before adding resources to it."
            )
        namespace = self._namespaces[resource.element.link]
        namespace.add_resource(resource)

    def get_resources(self):
        result = []
        for namespace in self._namespaces.values():
            result.extend(namespace.get_resources())
        return result

    def get_resource_by_link(self, element, link):
        if element.link not in self._namespaces:
            raise ValueError(
                f"Can't load element {element}. Element"
                f" {self._namespaces[element.link].element} is not found."
            )
        namespace = self._namespaces[element.link]
        return namespace.get_resource_by_link(link)

    def add_element(self, element):
        if element.link in self._namespaces:
            raise ValueError(
                f"Can't load element {element}. Element"
                f" {self._namespaces[element.link].element} already exists"
                " with the same UUID."
            )
        self._namespaces[element.link] = Namespace(element)

    def remove_element(self, element):
        if element.link not in self._namespaces:
            raise ValueError(
                f"Can't remove element {element}. Element does not exist."
            )

        del self._namespaces[element.link]

    def save_to_database(self):
        pass


element_engine = ElementEngine()
