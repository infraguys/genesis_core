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

import uuid as sys_uuid
from genesis_core.common import exceptions


class MachineAlreadyExistsError(exceptions.GCException):
    __template__ = "The machine {machine} already exists."
    machine: sys_uuid.UUID


class VolumeAlreadyExistsError(exceptions.GCException):
    __template__ = "The volume {volume} already exists."
    volume: sys_uuid.UUID


class VolumeNotFoundError(exceptions.GCException):
    __template__ = "The volume {volume} not found."
    volume: sys_uuid.UUID
