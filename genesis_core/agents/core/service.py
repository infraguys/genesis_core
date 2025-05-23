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
import logging
import subprocess

from gcl_looper.services import basic as looper_basic
from bazooka import exceptions as baz_exc

from genesis_core.common import system
from genesis_core.node import constants as nc
from genesis_core.agents.dm import models
from genesis_core.agents import constants as ac
from genesis_core.agents.clients import orch as clients


LOG = logging.getLogger(__name__)
FORCE_RELOAD_PAYLOAD_RATE = 30


class CoreAgentService(looper_basic.BasicService):

    def __init__(
        self,
        orch_api: clients.OrchAPI,
        payload_path: str = ac.PAYLOAD_PATH,
        iter_min_period=3,
        iter_pause=0.1,
    ):
        super().__init__(iter_min_period, iter_pause)
        self._system_uuid = system.system_uuid()
        self._orch_api = orch_api
        self._payload_path = payload_path

    def _reboot(self):
        subprocess.run("/bin/sh -c '(sleep 1 && reboot -f)&'", shell=True)

    def _register_agent(self, dp_payload: models.Payload):
        agent = models.CoreAgent.from_system_uuid()
        try:
            agent: models.CoreAgent = self._orch_api.agents.create(agent)
            LOG.info("Agent registered: %s", agent)
        except baz_exc.ConflictError:
            # Agent already registered
            pass

        self._orch_api.agents.register_payload(agent.uuid, dp_payload)
        LOG.info("Payload registered: %s", dp_payload)

    def _set_status(
        self,
        machine: models.Machine,
        node: models.Node | None = None,
    ) -> None:
        machine_update = {
            "status": machine.status,
            "description": machine.description,
        }
        node_update = {}

        if node is not None:
            node_update = {
                "status": node.status,
                "description": node.description,
            }

        self._orch_api.machines.update(machine.uuid, **machine_update)

        if node_update:
            self._orch_api.nodes.update(node.uuid, **node_update)

    def _set_error_status(
        self,
        machine: models.Machine,
        node: models.Node | None = None,
        description: str = "",
    ) -> None:
        if (
            machine.status != nc.MachineStatus.ERROR.value
            or node.status != nc.NodeStatus.ERROR.value
        ):
            node.description = machine.description = description
            node.status = nc.NodeStatus.ERROR.value
            machine.status = nc.MachineStatus.ERROR.value
            self._set_status(machine, node)

    def _actualize_machine(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        update = {}
        cp_machine = cp_payload.machine
        dp_machine = dp_payload.machine

        # Actualize cores
        if cp_machine.cores != dp_machine.cores:
            update["cores"] = dp_machine.cores

        # Actualize ram
        if cp_machine.ram != dp_machine.ram:
            update["ram"] = dp_machine.ram

        if update:
            self._orch_api.machines.update(dp_machine.uuid, **update)

        # Actualize interfaces
        if cp_payload.interfaces != dp_payload.interfaces:
            machine_client = self._orch_api.machines(cp_machine.uuid)
            # Create interfaces
            for iface in set(dp_payload.interfaces) - set(
                cp_payload.interfaces
            ):
                iface.machine = cp_machine.uuid
                machine_client.interfaces.create(iface)

            # Delete interfaces
            for iface in set(cp_payload.interfaces) - set(
                dp_payload.interfaces
            ):
                machine_client.interfaces.delete(iface.uuid)

            # Update interfaces
            for iface in set(cp_payload.interfaces) & set(
                dp_payload.interfaces
            ):
                machine_client.interfaces.update(iface.uuid, iface)

    def _clear_machine(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        dp_machine = dp_payload.machine
        dp_machine.status = nc.MachineStatus.IDLE.value
        dp_machine.description = ""
        dp_machine.boot = nc.BootAlternative.network.value

        self._orch_api.machines.update(
            dp_machine.uuid,
            boot=nc.BootAlternative.network.value,
            status=nc.MachineStatus.IDLE.value,
            image=None,
            description="",
        )

        self._reboot()

    def _actualize_image(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        # TODO(akremenetsky): Will be implemented later
        pass

    def _create_render(self, render: models.Render) -> None:
        # No need to create configuration file if it already exists
        # and have appropriate content, mode, user and group.
        if not render.does_exist_and_valid():
            render.save()

        update = {"status": models.cc.ConfigStatus.ACTIVE.value}
        self._orch_api.renders.update(render.uuid, **update)
        LOG.debug("Render %s was created", render.uuid)

    def _actualize_render(self, render: models.Render) -> None:
        dp_hash = render.calculate_dp_render_hash()
        cp_hash = render.calculate_cp_render_hash()
        render.render_hash = cp_hash

        if os.path.exists(render.path) and dp_hash == cp_hash:
            return

        render.save()
        update = {"status": models.cc.ConfigStatus.ACTIVE.value}
        self._orch_api.renders.update(render.uuid, **update)
        LOG.debug("Render %s was actualized", render.uuid)

    def _actualize_renders(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        # Create new renders
        for render in set(cp_payload.renders) - set(dp_payload.renders):
            try:
                self._create_render(render)
                dp_payload.renders.append(render)
            except Exception:
                LOG.exception("Error creating render %s", render.uuid)

        # Delete renders
        for render in set(dp_payload.renders) - set(cp_payload.renders):
            try:
                render.delete()
                dp_payload.renders.remove(render)
                LOG.debug("Render %s was deleted", render.uuid)
            except Exception:
                LOG.error("Error deleting render %s", render.uuid)

        # Update renders
        cp_render_map = {r.uuid: r for r in cp_payload.renders}
        dp_render_map = {r.uuid: r for r in dp_payload.renders}

        for r in set(cp_payload.renders) & set(dp_payload.renders):
            try:
                cp_render = cp_render_map[r.uuid]
                dp_render = dp_render_map[r.uuid]
                self._actualize_render(cp_render)
                dp_render.render_hash = cp_render.render_hash
            except Exception:
                LOG.exception("Error actualizing render %s", cp_render.uuid)

    def _actualize_node(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        cp_node = cp_payload.node
        dp_node = dp_payload.node

        # Don't consider this field for actualization
        # TODO(akremenetsky): Will be implemented later
        dp_payload.node = cp_node
        if dp_node != cp_node:
            dp_payload.node = cp_node

        # Actualize image
        # TODO(akremenetsky): Will be implemented later
        if (
            cp_node is not None
            and dp_node is not None
            and cp_node.image != dp_node.image
        ):
            return self._actualize_image(cp_payload, dp_payload)

        # The node was removed from the machine.
        # Clear the machine.
        if cp_node is None:
            return self._clear_machine(cp_payload, dp_payload)

    def _actualize_agent(
        self, cp_payload: models.Payload, dp_payload: models.Payload
    ) -> None:
        # Everything has been updated, save the updated_at time stamp
        dp_payload.payload_updated_at = cp_payload.payload_updated_at

    def _iteration(self):
        # Need for cleanup in some tricky or corner cases.
        # It's not a problem if the cleanup will be done a bit later.
        invalidate = self._iteration_number % FORCE_RELOAD_PAYLOAD_RATE == 0

        dp_payload = models.CoreAgent.collect_payload(
            self._payload_path, invalidate
        )

        # Check if the agent is registered
        try:
            cp_payload = self._orch_api.agents.get_target_payload(
                self._system_uuid, dp_payload
            )
        except baz_exc.NotFoundError:
            # Auto discovery mechanism
            self._register_agent(dp_payload)
            return

        # Nothing to do, payload is the same
        if cp_payload == dp_payload:
            return

        LOG.debug("Payload actualization is required")

        self._actualize_machine(cp_payload, dp_payload)
        self._actualize_node(cp_payload, dp_payload)
        self._actualize_renders(cp_payload, dp_payload)
        self._actualize_agent(cp_payload, dp_payload)

        # Save the payload after actualization
        models.CoreAgent.save_payload(dp_payload, self._payload_path)
