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

import enum
import typing as tp

DEF_SQL_LIMIT = 300
EP_MACHINE_POOL_DRIVERS = "gcn_machine_pool_driver"

BootType = tp.Literal["hd", "network", "cdrom"]


class NodeStatus(str, enum.Enum):
    NEW = "NEW"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    STARTED = "STARTED"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class MachineStatus(str, enum.Enum):
    NEW = "NEW"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    STARTED = "STARTED"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    ERROR = "ERROR"


class NodeType(str, enum.Enum):
    VM = "VM"
    HW = "HW"


class VolumeType(str, enum.Enum):
    QCOW2 = "QCOW2"


class MachineAgentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class MachinePoolStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    MAINTENANCE = "MAINTENANCE"


class BootAlternative(str, enum.Enum):
    hd0 = "hd0"
    hd1 = "hd1"
    hd2 = "hd2"
    hd3 = "hd3"
    hd4 = "hd4"
    hd5 = "hd5"
    hd6 = "hd6"
    hd7 = "hd7"
    cdrom = "cdrom"
    network = "network"

    @property
    def boot_type(self) -> BootType:
        if self.value.startswith("hd"):
            return "hd"
        elif self.value == "cdrom":
            return "cdrom"
        elif self.value == "network":
            return "network"

        raise ValueError(f"Invalid boot alternative: {self.value}")
