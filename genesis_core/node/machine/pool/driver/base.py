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
    ) -> models.Machine:
        """Create a new machine."""

    @abc.abstractmethod
    def delete_machine(
        self, machine: models.Machine, delete_volumes: bool = True
    ) -> None:
        """Delete the machine from data plane."""

    @abc.abstractmethod
    def actualize_machine(
        self, target_state: models.Machine, actual_state: models.Machine
    ) -> None:
        """Actualize the machine."""

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
    ) -> models.Machine:
        """Create a machine."""
        return machine

    def delete_machine(
        self, machine: models.Machine, delete_volumes: bool = True
    ) -> None:
        pass

    def actualize_machine(
        self, target_state: models.Machine, actual_state: models.Machine
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
