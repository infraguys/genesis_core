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

from genesis_core.compute.dm import models

LOCAL_GC_HOST = "core.local.genesis-core.tech"
LOCAL_GC_ORCH_API = "http://core.local.genesis-core.tech:11011"
LOCAL_GC_STATUS_API = "http://core.local.genesis-core.tech:11012"


class MachineNetboot(models.Machine):
    __custom_properties__ = {
        "gc_host": types.String(max_length=255),
        "gc_orch_api": types.String(max_length=255),
        "gc_status_api": types.String(max_length=255),
        "kernel": types.AllowNone(types.String(max_length=255)),
        "initrd": types.AllowNone(types.String(max_length=255)),
    }

    def __init__(
        self,
        gc_host: str = LOCAL_GC_HOST,
        gc_orch_api: str = LOCAL_GC_ORCH_API,
        gc_status_api: str = LOCAL_GC_STATUS_API,
        kernel: str | None = None,
        initrd: str | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.set_netboot_params(gc_host, gc_orch_api, gc_status_api, kernel, initrd)

    @classmethod
    def restore_from_storage(
        cls,
        gc_host: str = LOCAL_GC_HOST,
        gc_orch_api: str = LOCAL_GC_ORCH_API,
        gc_status_api: str = LOCAL_GC_STATUS_API,
        kernel: str | None = None,
        initrd: str | None = None,
        **kwargs,
    ):
        obj = super().restore_from_storage(**kwargs)
        obj.set_netboot_params(gc_host, gc_orch_api, gc_status_api, kernel, initrd)
        return obj

    def set_netboot_params(
        self,
        gc_host: str,
        gc_orch_api: str,
        gc_status_api: str,
        kernel: str | None,
        initrd: str | None,
    ) -> None:
        self.gc_host = gc_host
        self.gc_orch_api = gc_orch_api
        self.gc_status_api = gc_status_api

        # Use tftp by default
        if kernel is None:
            kernel = f"tftp://{gc_host}/bios/vmlinuz"
        if initrd is None:
            initrd = f"tftp://{gc_host}/bios/initrd.img"

        self.kernel = kernel
        self.initrd = initrd
