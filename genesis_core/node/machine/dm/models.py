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

from genesis_core.node.dm import models


class Machine(models.Machine):
    node = relationships.relationship(models.Node, prefetch=True)
    pool = relationships.relationship(models.MachinePool, prefetch=True)

    def cast_to_base(self) -> models.Machine:
        view = self.dump_to_simple_view(skip=("node", "pool"))
        view["node"] = str(self.node.uuid)
        view["pool"] = str(self.pool.uuid)
        return models.Machine.restore_from_simple_view(**view)
