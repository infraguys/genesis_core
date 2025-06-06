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
from __future__ import annotations

import typing as tp
import uuid as sys_uuid

from restalchemy.dm import models
from restalchemy.dm import filters as dm_filters
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from restalchemy.storage.sql import orm
from restalchemy.storage.sql import engines

from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.common.dm import models as cm
from genesis_core.node.dm import models as nm
from genesis_core.config import constants as cc


class AbstractTarget(types_dynamic.AbstractKindModel, models.SimpleViewMixin):

    def target_nodes(self) -> tp.List[sys_uuid.UUID]:
        """Returns list of target nodes where config should be deployed."""
        return []

    def owners(self) -> tp.List[sys_uuid.UUID]:
        """Return list of owners objects where config bind to.

        For instance, the simplest case if an ordinary node config.
        In that case, the owner and target is the node itself.
        A more complex case is when a config is bound to a node set.
        In this case the owner is the set and the targets are all nodes
        in this set.
        """
        return []

    def are_owners_alive(self) -> bool:
        raise NotImplementedError()


class AbstractContentor(
    types_dynamic.AbstractKindModel, models.SimpleViewMixin
):

    def render(self) -> str:
        return ""


class NodeTarget(AbstractTarget):
    KIND = "node"

    node = properties.property(types.UUID(), required=True)

    @classmethod
    def from_node(cls, node: sys_uuid.UUID) -> "NodeTarget":
        return cls(node=node)

    def target_nodes(self) -> tp.List[sys_uuid.UUID]:
        return [self.node]

    def owners(self) -> tp.List[sys_uuid.UUID]:
        """It's the simplest case with an ordinary node config.

        In that case, the owner and target is the node itself.
        If owners are deleted, the config will be deleted as well.
        """
        return [self.node]

    def _fetch_nodes(self) -> tp.List[nm.Node]:
        return nm.Node.objects.get_all(filters={"uuid": str(self.node)})

    def are_owners_alive(self) -> bool:
        return bool(self._fetch_nodes())


class TextBodyConfig(AbstractContentor):
    KIND = "text"

    content = properties.property(types.String(), required=True, default="")

    @classmethod
    def from_text(cls, text: str) -> "TextBodyConfig":
        return cls(content=text)

    def render(self) -> str:
        return self.content


class TemplateBodyConfig(AbstractContentor):
    KIND = "template"

    template = properties.property(types.String(), required=True, default="")
    variables = properties.property(types.Dict(), default=dict)

    def render(self) -> str:
        # TODO(akremenetsky): Will be added later
        raise NotImplementedError()


class OnChangeNoAction(
    types_dynamic.AbstractKindModel, models.SimpleViewMixin
):
    KIND = "no_action"


class OnChangeShell(types_dynamic.AbstractKindModel, models.SimpleViewMixin):
    KIND = "shell"

    command = properties.property(
        types.String(max_length=262144), required=True, default=""
    )

    @classmethod
    def from_command(cls, command: str) -> "OnChangeShell":
        return cls(command=command)


class Config(
    cm.ModelWithFullAsset,
    orm.SQLStorableMixin,
    ua_models.TargetResourceMixin,
):
    __tablename__ = "config_configs"

    path = properties.property(
        types.String(min_length=1, max_length=255),
        required=True,
    )
    status = properties.property(
        types.Enum([s.value for s in cc.ConfigStatus]),
        default=cc.ConfigStatus.NEW.value,
    )
    target = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(NodeTarget),
        ),
        required=True,
    )
    body = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(TextBodyConfig),
            types_dynamic.KindModelType(TemplateBodyConfig),
        ),
        required=True,
    )
    on_change = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(OnChangeNoAction),
            types_dynamic.KindModelType(OnChangeShell),
        ),
        default=OnChangeNoAction,
    )
    mode = properties.property(
        types.Enum([m.value for m in cc.FileMode]),
        default=cc.FileMode.o644.value,
    )
    owner = properties.property(
        types.String(max_length=128),
        default="root",
    )
    group = properties.property(
        types.String(max_length=128),
        default="root",
    )

    def target_nodes(self) -> tp.List[sys_uuid.UUID]:
        return self.target.target_nodes()

    def target_owners(self) -> tp.List[sys_uuid.UUID]:
        return self.target.owners()

    def render(self, node: sys_uuid.UUID) -> ua_models.TargetResource:
        # FIXME(akremenetsky): The `node` parameter will
        # be used in the future for node sets to make a
        # particular rendering for each node.
        # `content = self.body.render(node=node)`
        content = self.body.render()
        render_uuid = sys_uuid.uuid5(node, self.path)

        config_view = self.dump_to_simple_view(skip=("uuid",))
        render = Render.restore_from_simple_view(
            uuid=render_uuid,
            content=content,
            **{
                k: v
                for k, v in config_view.items()
                if k in Render.properties.properties
            },
        )

        resource = render.to_ua_resource("render", master=self.uuid)
        resource.calculate_hash()
        return resource

    @classmethod
    def get_new_configs(
        cls, limit: int = cc.DEFAULT_SQL_LIMIT
    ) -> list["Config"]:
        expression = (
            "SELECT "
            "    config_configs.uuid as uuid "
            "FROM config_configs LEFT JOIN ua_target_resources ON "
            "    config_configs.uuid = ua_target_resources.uuid "
            "WHERE ua_target_resources.uuid is NULL "
            "LIMIT %s;"
        )
        params = (limit,)

        engine = engines.engine_factory.get_engine()
        with engine.session_manager() as session:
            curs = session.execute(expression, params)
            response = curs.fetchall()

        if not response:
            return []

        return cls.objects.get_all(
            filters={"uuid": dm_filters.In(str(r["uuid"]) for r in response)},
        )

    @classmethod
    def get_updated_configs(
        cls, limit: int = cc.DEFAULT_SQL_LIMIT
    ) -> list["Config"]:
        expression = (
            "SELECT "
            "    config_configs.uuid as uuid "
            "FROM config_configs INNER JOIN ua_target_resources ON  "
            "    config_configs.uuid = ua_target_resources.uuid "
            "WHERE config_configs.updated_at != ua_target_resources.tracked_at "
            "LIMIT %s;"
        )
        params = (limit,)

        engine = engines.engine_factory.get_engine()
        with engine.session_manager() as session:
            curs = session.execute(expression, params)
            response = curs.fetchall()

        if not response:
            return []

        return cls.objects.get_all(
            filters={"uuid": dm_filters.In(str(r["uuid"]) for r in response)},
        )

    @classmethod
    def get_deleted_config_renders(
        cls, limit: int = cc.DEFAULT_SQL_LIMIT
    ) -> list[ua_models.TargetResource]:
        expression = (
            "SELECT "
            "    ua_target_resources.uuid as uuid "
            "FROM ua_target_resources LEFT JOIN config_configs ON  "
            "    ua_target_resources.uuid = config_configs.uuid  "
            "WHERE ua_target_resources.kind = 'config' "
            "    AND config_configs.uuid is NULL "
            "LIMIT %s;"
        )
        params = (limit,)

        engine = engines.engine_factory.get_engine()
        with engine.session_manager() as session:
            curs = session.execute(expression, params)
            response = curs.fetchall()

        if not response:
            return []

        return ua_models.TargetResource.objects.get_all(
            filters={"uuid": dm_filters.In(str(r["uuid"]) for r in response)},
        )


class Render(
    models.ModelWithUUID,
    ua_models.TargetResourceMixin,
):
    content = properties.property(types.String(), required=True)
    path = properties.property(
        types.String(min_length=1, max_length=512),
        required=True,
    )
    mode = properties.property(types.String(max_length=4), default="0644")
    owner = properties.property(
        types.String(max_length=128),
        default="root",
    )
    group = properties.property(
        types.String(max_length=128),
        default="root",
    )
    on_change = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(OnChangeNoAction),
            types_dynamic.KindModelType(OnChangeShell),
        ),
        default=OnChangeNoAction,
    )
