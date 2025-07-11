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

DEFAULT_SQL_LIMIT = 100
CONFIG_KIND = "config"
RENDER_KIND = "render"


class ConfigStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class FilePermission(enum.Flag):
    R = 4
    W = 2
    X = 1

    ALL = R | W | X

    @classmethod
    def combinations(cls) -> tp.Tuple[int]:
        return tuple(range(8))


FileMode = enum.Enum(
    "FileMode",
    [
        (f"o{u}{g}{o}", f"0{u}{g}{o}")
        for u in FilePermission.combinations()
        for g in FilePermission.combinations()
        for o in FilePermission.combinations()
    ],
)
