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
from genesis_core.common.dm import models as cm


class Subnet(models.Subnet, cm.CastToBaseMixin):
    __cast_fields__ = ("network",)

    network = relationships.relationship(models.Network, prefetch=True)


class Port(models.Port, cm.CastToBaseMixin):
    __cast_fields__ = ("node", "machine", "subnet")

    subnet = relationships.relationship(Subnet, prefetch=True)
    node = relationships.relationship(models.Node, prefetch=True)
    machine = relationships.relationship(models.Machine, prefetch=True)


class HWNodeWithoutPorts(models.HWNodeWithoutPorts):
    node = relationships.relationship(models.Node, prefetch=True)
    machine = relationships.relationship(models.Machine, prefetch=True)
    iface = relationships.relationship(models.Interface, prefetch=True)
