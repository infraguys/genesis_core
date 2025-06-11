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

import abc
import uuid as sys_uuid
import typing as tp

from genesis_core.node.dm import models


class AbstractPoolDriver(abc.ABC):

    @abc.abstractmethod
    def list_machines(self) -> tp.List[models.Machine]:
        """Return machine list from data plane."""

    @abc.abstractmethod
    def create_machine(
        self,
        machine: models.Machine,
        volumes: tp.Iterable[models.MachineVolume],
        ports: tp.Iterable[models.Port],
    ) -> models.Machine:
        """Create a new machine."""

    @abc.abstractmethod
    def delete_machine(
        self, machine: models.Machine, delete_volumes: bool = True
    ) -> None:
        """Delete the machine from data plane."""

    @abc.abstractmethod
    def create_volume(
        self, volume: models.MachineVolume
    ) -> models.MachineVolume:
        """Create a new volume."""

    @abc.abstractmethod
    def delete_volume(self, volume: models.MachineVolume) -> None:
        """Delete the volume from data plane."""

    @abc.abstractmethod
    def list_volumes(
        self, machine: models.Machine
    ) -> tp.Iterable[models.MachineVolume]:
        """Return volume list from data plane."""

    @abc.abstractmethod
    def get_volume(
        self, machine: sys_uuid.UUID, uuid: sys_uuid.UUID
    ) -> models.MachineVolume:
        """Get the machine volume by uuid."""

    @abc.abstractmethod
    def set_machine_cores(self, machine: models.Machine, cores: int) -> None:
        """Set machine cores."""

    @abc.abstractmethod
    def set_machine_ram(self, machine: models.Machine, ram: int) -> None:
        """Set machine ram."""

    @abc.abstractmethod
    def reset_machine(self, machine: models.Machine) -> None:
        """Reset the machine."""


class DummyPoolDriver(AbstractPoolDriver):
    SPEC = {"driver": "dummy"}

    def __init__(self, pool: models.MachinePool):
        if pool.driver_spec != self.SPEC:
            raise ValueError(f"Invalid driver spec: {pool.driver_spec}")

    def list_machines(self) -> tp.List[models.Machine]:
        """Create a machine."""
        return []

    def create_machine(
        self,
        machine: models.Machine,
        volumes: tp.Iterable[models.MachineVolume],
        ports: tp.Iterable[models.Port],
    ) -> models.Machine:
        """Create a machine."""
        return machine

    def delete_machine(
        self, machine: models.Machine, delete_volumes: bool = True
    ) -> None:
        pass

    def create_volume(
        self, volume: models.MachineVolume
    ) -> models.MachineVolume:
        """Create a new volume."""
        pass

    def delete_volume(self, volume: models.MachineVolume) -> None:
        """Delete the volume from data plane."""
        pass

    def list_volumes(
        self, machine: models.Machine
    ) -> tp.Iterable[models.MachineVolume]:
        """Return volume list from data plane."""
        return []

    def get_volume(
        self, machine: sys_uuid.UUID, uuid: sys_uuid.UUID
    ) -> models.MachineVolume:
        """Get the machine volume by uuid."""

    def set_machine_cores(self, machine: models.Machine, cores: int) -> None:
        """Set machine cores."""

    def set_machine_ram(self, machine: models.Machine, ram: int) -> None:
        """Set machine ram."""

    def reset_machine(self, machine: models.Machine) -> None:
        """Reset the machine."""
