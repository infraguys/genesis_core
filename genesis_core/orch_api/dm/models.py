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

LOCAL_GC_HOST = "localhost"
LOCAL_GC_PORT = 11011


class Netboot(node_models.Netboot):
    __custom_properties__ = {
        "gc_host": types.String(max_length=255),
        "gc_port": types.Integer(),
        "kernel": types.AllowNone(types.String(max_length=255)),
        "initrd": types.AllowNone(types.String(max_length=255)),
    }

    def __init__(
        self,
        gc_host: str = LOCAL_GC_HOST,
        gc_port: int = LOCAL_GC_PORT,
        kernel: str | None = None,
        initrd: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.set_netboot_params(gc_host, gc_port, kernel, initrd)

    @classmethod
    def restore_from_storage(
        cls,
        gc_host: str = LOCAL_GC_HOST,
        gc_port: int = LOCAL_GC_PORT,
        kernel: str | None = None,
        initrd: str | None = None,
        **kwargs,
    ):
        obj = super().restore_from_storage(**kwargs)
        obj.set_netboot_params(gc_host, gc_port, kernel, initrd)
        return obj

    def set_netboot_params(
        self,
        gc_host: str,
        gc_port: int,
        kernel: str | None,
        initrd: str | None,
    ) -> None:
        self.gc_host = gc_host
        self.gc_port = gc_port

        # Use tftp by default
        if kernel is None:
            kernel = f"tftp://{gc_host}/bios/vmlinuz"
        if initrd is None:
            initrd = f"tftp://{gc_host}/bios/initrd.img"

        self.kernel = kernel
        self.initrd = initrd


class Node(node_models.Node):
    pass


class Machine(node_models.Machine):
    pass
