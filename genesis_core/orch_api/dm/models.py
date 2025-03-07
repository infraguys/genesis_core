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

from restalchemy.dm import types

from genesis_core.node.dm import models as node_models

# TODO(akremenetsky): Remove these default values
# after support of multiple stands
GC_HOST = "10.20.0.2"
GC_PORT = 11011


class Netboot(node_models.Netboot):
    __custom_properties__ = {
        "gc_host": types.String(max_length=255),
        "gc_port": types.Integer(),
    }

    def __init__(
        self, gc_host: str = GC_HOST, gc_port: int = GC_PORT, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.gc_host = gc_host
        self.gc_port = gc_port

    @classmethod
    def restore_from_storage(
        cls, gc_host: str = GC_HOST, gc_port: int = GC_PORT, **kwargs
    ):
        obj = super().restore_from_storage(**kwargs)
        obj.gc_host = gc_host
        obj.gc_port = gc_port
        return obj


class Node(node_models.Node):
    pass


class Machine(node_models.Machine):
    pass
