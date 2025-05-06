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

import os
import pwd
import grp
import datetime
import json
import logging
import hashlib
import subprocess
import typing as tp

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import types
from restalchemy.dm import types_dynamic

from genesis_core.common import system
from genesis_core.common import constants as c
from genesis_core.agents import constants as ac
from genesis_core.node.dm import models as nm
from genesis_core.node import constants as nc
from genesis_core.config import constants as cc
from genesis_core.config.dm import models as config_models
from genesis_core.orch_api import utils as orch_utils


LOG = logging.getLogger(__name__)


class Machine(nm.Machine):
    KIND = "machine"

    @classmethod
    def from_system(cls):
        uuid = system.system_uuid()
        cores = system.get_cores()
        ram = system.get_memory()

        return cls(
            uuid=uuid,
            firmware_uuid=uuid,
            cores=cores,
            ram=ram,
            status=nc.MachineStatus.IDLE.value,
            boot=nc.BootAlternative.network.value,
            project_id=c.SERVICE_PROJECT_ID,
            # TODO(akremenetsky): Determine machine type
            machine_type=nc.NodeType.HW.value,
        )


class Node(nm.Node):
    KIND = "node"


class AbstractRenderHooks:
    def on_change(self) -> None:
        raise NotImplementedError()


class OnChangeNoAction(config_models.OnChangeNoAction, AbstractRenderHooks):
    def on_change(self) -> None:
        # Do nothing
        pass


class OnChangeShell(config_models.OnChangeShell, AbstractRenderHooks):
    def on_change(self) -> None:
        subprocess.check_output(self.command, shell=True)


class Render(models.ModelWithUUID, models.SimpleViewMixin):
    """Render of the configuration file.

    Actualy the Render class may be represented in two roles:
    1) The target configuration file from the CP.
    2) A descriptor of the configuration file from file system.
       The descriptor since it doesn't keep content but only
       meta information like path, mode, owner, group and so on.
    """

    path = properties.property(
        types.String(min_length=1, max_length=512),
        required=True,
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
    on_change = properties.property(
        types_dynamic.KindModelSelectorType(
            types_dynamic.KindModelType(OnChangeNoAction),
            types_dynamic.KindModelType(OnChangeShell),
        ),
    )
    content = properties.property(
        types.AllowNone(types.String()), default=None
    )
    render_hash = properties.property(types.String(max_length=255), default="")

    @property
    def is_valid_hash(self) -> bool:
        """Calculate hash of the render and check if it the same."""
        return self.render_hash == self.calculate_dp_render_hash()

    def save(self):
        """Save the render to the file system."""
        if self.content is None:
            raise ValueError("Render content is empty")

        # Create the directory if it doesn't exist
        if not os.path.exists(os.path.dirname(self.path)):
            os.makedirs(os.path.dirname(self.path))

        # Save the content
        with open(self.path, "w") as f:
            f.write(self.content)

        # Set the file mode, owner and group
        mode = int(self.mode, base=8)

        try:
            owner = pwd.getpwnam(self.owner).pw_uid
        except KeyError:
            raise ValueError(f"User {self.owner} does not exist")

        try:
            group = grp.getgrnam(self.group).gr_gid
        except KeyError:
            raise ValueError(f"Group {self.group} does not exist")

        os.chmod(self.path, mode)
        os.chown(self.path, owner, group)

        self.on_change.on_change()

        # Calculate hash
        self.render_hash = self.calculate_dp_render_hash()
        LOG.info("Render saved to %s", self.path)

    def delete(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def calculate_dp_render_hash(
        self, hash_method: tp.Callable[[str], str] = hashlib.sha256
    ) -> str:
        """Calculate render hash from data plane."""
        m = hash_method()

        if not os.path.exists(self.path):
            return m.hexdigest()

        # Read the content by chunks and calculate hash
        with open(self.path, "rb") as f:
            chunk_size = 1048576  # 1MB
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                m.update(chunk)

        # Read the file mode, owner and group
        stat = os.stat(self.path)
        mode = oct(stat.st_mode)[-3:]
        owner = pwd.getpwuid(stat.st_uid).pw_name
        group = grp.getgrgid(stat.st_gid).gr_name

        data = {
            "uuid": str(self.uuid),
            "path": self.path,
            "mode": "0" + mode,
            "owner": owner,
            "group": group,
            "on_change": self.on_change.dump_to_simple_view(),
        }
        m.update(
            json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        )
        return m.hexdigest()

    def calculate_cp_render_hash(
        self, hash_method: tp.Callable[[str], str] = hashlib.sha256
    ) -> str:
        """Calculate render hash from control plane."""
        m = hash_method()
        m.update(self.content.encode("utf-8"))

        data = {
            "uuid": str(self.uuid),
            "path": self.path,
            "mode": self.mode,
            "owner": self.owner,
            "group": self.group,
            "on_change": self.on_change.dump_to_simple_view(),
        }
        m.update(
            json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
        )
        return m.hexdigest()

    def does_exist_and_valid(self) -> bool:
        return (
            os.path.exists(self.path)
            and self.calculate_cp_render_hash()
            == self.calculate_dp_render_hash()
        )

    def exclude_dp_related(self):
        """Exclude DP related fileds from the render."""
        # Actually we need to exclude the mode, group,
        # owner as well but just keep default values for now
        self.content = None


class Payload(models.Model, models.SimpleViewMixin):
    machine = properties.property(
        types.AllowNone(types_dynamic.KindModelType(Machine)), default=None
    )

    node = properties.property(
        types.AllowNone(types_dynamic.KindModelType(Node)), default=None
    )
    renders = properties.property(
        types.TypedList(
            types_dynamic.KindModelType(Render),
        ),
        default=list,
    )
    interfaces = properties.property(
        types.TypedList(
            types_dynamic.KindModelType(nm.Interface),
        ),
        default=list,
    )
    ports = properties.property(
        types.TypedList(
            types_dynamic.KindModelType(nm.Port),
        ),
        default=list,
    )

    # This field is used for CP payloads
    payload_hash = properties.property(
        types.String(max_length=255), default=""
    )
    payload_updated_at = properties.property(
        types.UTCDateTimeZ(),
        default=lambda: datetime.datetime(
            1970, 1, 1, 0, 1, tzinfo=datetime.timezone.utc
        ),
    )

    def __eq__(self, other: "Payload") -> bool:
        return self.__hash__() == other.__hash__()

    def __hash__(self) -> int:
        if self.payload_hash:
            return hash((self.payload_hash, self.payload_updated_at))

        return hash((self.calculate_payload_hash(), self.payload_updated_at))

    def calculate_payload_hash(
        self, hash_method: tp.Callable[[str], str] = hashlib.sha256
    ) -> str:
        """Calculate payload hash using dedicated fields."""
        payload = {"machine": {}}

        # Base payload object
        if self.machine is not None:
            payload["machine"] = self.machine.dump_to_simple_view()

        if self.node is not None:
            payload["node"] = self.node.dump_to_simple_view()
            # Copy these fields from the node so far
            payload["machine"]["node"] = str(self.node.uuid)
            payload["machine"]["image"] = self.node.image

        if self.renders:
            payload["renders"] = [r.render_hash for r in self.renders]

        if interfaces := self.interfaces:
            payload["interfaces"] = [
                i.dump_to_simple_view() for i in interfaces
            ]

        return orch_utils.calculate_payload_hash(payload, hash_method)

    def update_payload_hash(self):
        self.payload_hash = self.calculate_payload_hash()

    def exclude_dp_related(self):
        for render in self.renders:
            render.exclude_dp_related()

        self.interfaces = []


class CoreAgent(nm.CoreAgent):

    @classmethod
    def from_system_uuid(cls):
        uuid = system.system_uuid()
        return cls(
            uuid=uuid,
            name=f"Core Agent {str(uuid)[:8]}",
        )

    @classmethod
    def empty_payload(cls) -> Payload:
        interfaces = nm.Interface.from_system()
        return Payload(
            machine=Machine.from_system(), node=None, interfaces=interfaces
        )

    @classmethod
    def collect_payload(
        cls, payload_path: str, invalidate_payload_date: bool = False
    ) -> Payload:
        """Collect payload from the data plane."""
        if not os.path.exists(payload_path):
            payload: Payload = cls.empty_payload()
        else:
            # Load base from the payload file
            with open(payload_path) as f:
                payload_data = json.load(f)
                payload: Payload = Payload.restore_from_simple_view(
                    **payload_data
                )

        if invalidate_payload_date:
            payload.payload_updated_at = datetime.datetime(
                1970, 1, 1, 0, 1, tzinfo=datetime.timezone.utc
            )

        # Collect interfaces
        payload.interfaces = nm.Interface.from_system()
        for iface in payload.interfaces:
            iface.machine = payload.machine.uuid

        # Collect renders
        for render in payload.renders:
            # Check if the render has been changed.
            # The simplest solution is used right now. If the any part of
            # the payload has been changes, fetch it from CP again.
            if not render.is_valid_hash:
                empty = cls.empty_payload()
                empty.update_payload_hash()
                LOG.info("Payload has been changed. Fetch it from CP")
                return empty

        payload.update_payload_hash()
        return payload

    @classmethod
    def save_payload(cls, payload: Payload, payload_path: str) -> None:
        """Collect payload from the data plane."""
        payload.update_payload_hash()
        payload.exclude_dp_related()

        # Create missing directories
        payload_dir = os.path.dirname(payload_path)
        if not os.path.exists(payload_dir):
            os.makedirs(payload_dir)

        with open(payload_path, "w") as f:
            payload_data = payload.dump_to_simple_view()
            LOG.debug("Saving payload: %s", payload_data)
            json.dump(payload_data, f, indent=2)
