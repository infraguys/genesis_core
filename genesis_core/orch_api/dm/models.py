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

import copy
import json
import hashlib
import datetime
import typing as tp
import uuid as sys_uuid

from restalchemy.dm import types
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.storage.sql import engines
from restalchemy.dm import filters as dm_filters
from restalchemy.common import exceptions as ra_common_exc

from genesis_core.node.dm import models
from genesis_core.config.dm import models as cm
from genesis_core.common import constants as c
from genesis_core.orch_api import utils as orch_utils

LOCAL_GC_HOST = "localhost"
LOCAL_GC_PORT = 11011


class Netboot(models.Netboot):
    __custom_properties__ = {
        "gc_host": types.String(max_length=255),
        "gc_port": types.Integer(),
        "kernel": types.AllowNone(types.String(max_length=255)),
        "initrd": types.AllowNone(types.String(max_length=255)),
    }

    def __init__(
        self,
        gc_host: str = LOCAL_GC_HOST,
        gc_port: int = LOCAL_GC_PORT,
        kernel: str | None = None,
        initrd: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.set_netboot_params(gc_host, gc_port, kernel, initrd)

    @classmethod
    def restore_from_storage(
        cls,
        gc_host: str = LOCAL_GC_HOST,
        gc_port: int = LOCAL_GC_PORT,
        kernel: str | None = None,
        initrd: str | None = None,
        **kwargs,
    ):
        obj = super().restore_from_storage(**kwargs)
        obj.set_netboot_params(gc_host, gc_port, kernel, initrd)
        return obj

    def set_netboot_params(
        self,
        gc_host: str,
        gc_port: int,
        kernel: str | None,
        initrd: str | None,
    ) -> None:
        self.gc_host = gc_host
        self.gc_port = gc_port

        # Use tftp by default
        if kernel is None:
            kernel = f"tftp://{gc_host}/bios/vmlinuz"
        if initrd is None:
            initrd = f"tftp://{gc_host}/bios/initrd.img"

        self.kernel = kernel
        self.initrd = initrd


class Node(models.Node):

    @classmethod
    def get_state(cls, uuid: sys_uuid.UUID) -> tp.Dict[str, tp.Any]:
        node = cls.objects.get_one(filters={"uuid": dm_filters.EQ(str(uuid))})
        ports = models.Port.objects.get_all(
            filters={"node": dm_filters.EQ(str(uuid))}
        )
        renders = Render.objects.get_all(
            filters={"node": dm_filters.EQ(str(uuid))}
        )
        return {
            "node": node.dump_to_simple_view(),
            "ports": [p.dump_to_simple_view() for p in ports],
            "renders": [r.to_agent_payload() for r in renders],
        }


class Machine(models.Machine):

    @classmethod
    def from_agent_payload(cls, payload: tp.Dict[str, tp.Any]) -> "Machine":
        if "machine" not in payload:
            raise ValueError("Machine not found in payload")

        return cls.restore_from_simple_view(**payload["machine"])


class Interface(models.Interface):
    machine = relationships.relationship(Machine, prefetch=True)

    @classmethod
    def from_agent_payload(
        cls, machine: Machine, payload: tp.Dict[str, tp.Any]
    ) -> tp.List["Interface"]:
        interfaces = []

        for iface in payload.get("interfaces", ()):
            i = cls.restore_from_simple_view(machine=machine, **iface)
            interfaces.append(i)

        return interfaces


class OrchRenderModel(cm.Render):
    config = properties.property(types.UUID(), required=True)


class Render(cm.Render):

    def to_agent_payload(self) -> tp.Dict[str, tp.Any]:
        return {
            "uuid": str(self.uuid),
            "content": self.content,
            "path": self.config.path,
            "mode": self.config.mode,
            "owner": self.config.owner,
            "group": self.config.group,
            "on_change": self.config.on_change.dump_to_simple_view(),
        }

    @classmethod
    def render_payload_hash(
        cls,
        render: tp.Dict[str, tp.Any],
        hash_method: tp.Callable[[str], str] = hashlib.sha256,
    ) -> str:
        """Calculate render hash using dedicated fields."""
        m = hash_method()
        m.update(render["content"].encode("utf-8"))

        content = render.pop("content")

        m.update(
            json.dumps(render, separators=(",", ":"), sort_keys=True).encode()
        )

        render["content"] = content
        return m.hexdigest()


class CoreAgent(models.CoreAgent):

    machine = relationships.relationship(Machine, prefetch=True)

    @classmethod
    def calculate_payload_hash(
        cls,
        payload: tp.Dict[str, tp.Any],
        hash_method: tp.Callable[[str], str] = hashlib.sha256,
    ) -> str:
        """Calculate payload hash using dedicated fields."""
        payload = copy.deepcopy(payload)

        if renders := payload.get("renders"):
            # The reason why it's used 'double' hash is optimization on
            # the agent side. For the agent it's easier to calculate hash
            # per render and then calculate common hash. So do the same here.
            payload["renders"] = [
                Render.render_payload_hash(r, hash_method) for r in renders
            ]

        return orch_utils.calculate_payload_hash(payload, hash_method)

    def _get_payload(self) -> tp.Dict[str, tp.Any]:
        state = {
            "payload_updated_at": self.payload_updated_at.strftime(
                c.DEFAULT_DATETIME_FORMAT
            ),
            "machine": self.machine.dump_to_simple_view(),
        }

        if self.machine.node:
            node_state = Node.get_state(self.machine.node)
            state.update(node_state)

        interfaces = models.Interface.objects.get_all(
            filters={"machine": dm_filters.EQ(str(self.machine.uuid))}
        )
        state["interfaces"] = [i.dump_to_simple_view() for i in interfaces]

        state["payload_hash"] = self.calculate_payload_hash(state)
        return state

    def _get_short_payload(self, payload_hash: str) -> tp.Dict[str, tp.Any]:
        state = {
            "payload_updated_at": self.payload_updated_at.strftime(
                c.DEFAULT_DATETIME_FORMAT
            ),
            "payload_hash": payload_hash,
        }

        return state

    def get_payload(
        self,
        payload_hash: str = "",
        payload_updated_at: datetime.datetime | None = None,
    ) -> tp.Dict[str, tp.Any]:
        # The agent has state. Check if the state has changed
        latest_updated_at = self.latest_updated_at()

        # Rely on the latest_updated_at
        if payload_updated_at == latest_updated_at:
            return self._get_short_payload(payload_hash)

        # The agent and system states are different.
        # Firstly get the state then update the payload_updated_at.
        state = self._get_payload()
        state["payload_updated_at"] = latest_updated_at.strftime(
            c.DEFAULT_DATETIME_FORMAT
        )
        self.payload_updated_at = latest_updated_at
        self.update()

        return state

    def latest_updated_at(self) -> datetime.datetime:
        payload_expression = (
            "SELECT MAX(max) AS latest_updated_at "
            "FROM ("
            "    SELECT MAX(updated_at) FROM nodes WHERE uuid = %s "
            "    UNION ALL "
            "    SELECT MAX(updated_at) FROM machines WHERE node = %s "
            "    UNION ALL "
            "    SELECT MAX(updated_at) FROM compute_ports WHERE node = %s "
            "    UNION ALL "
            "    SELECT MAX(updated_at) FROM config_renders WHERE node = %s "
            ");"
        )
        machine_expression = (
            "SELECT MAX(max) AS latest_updated_at "
            "FROM ("
            "    SELECT MAX(updated_at) FROM machines WHERE uuid = %s "
            "    UNION ALL "
            "    SELECT MAX(updated_at) FROM compute_ports WHERE machine = %s "
            ");"
        )
        if self.machine is None:
            raise ra_common_exc.CanNotFindResourceByModel(model=self)

        if self.machine.node is None:
            expression = machine_expression
            params = [str(self.uuid)] * 2
        else:
            expression = payload_expression
            params = [str(self.machine.node)] * 4

        engine = engines.engine_factory.get_engine()
        with engine.session_manager() as session:
            curs = session.execute(expression, params)
            latest_updated_at = curs.fetchone()["latest_updated_at"]
            latest_updated_at = latest_updated_at.replace(
                tzinfo=datetime.timezone.utc
            )
            return latest_updated_at
