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

from restalchemy.dm import relationships

from genesis_core.compute.dm import models
from genesis_core.common.dm import models as cm


class Machine(models.Machine, cm.CastToBaseMixin):
    __cast_fields__ = ("node", "pool")

    node = relationships.relationship(models.Node, prefetch=True)
    pool = relationships.relationship(models.MachinePool, prefetch=True)
