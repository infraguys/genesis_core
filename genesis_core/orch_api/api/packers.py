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

from restalchemy.api import packers

from genesis_core.node import constants as nc
from genesis_core.orch_api.dm import models


_from_net_template = """#!ipxe
:kernel
kernel {kernel} showopts ip=dhcp net.ifnames=0 biosdevname=0 gc_base_url=http://{gc_host}:{gc_port} || goto kernel

:initrd
initrd {initrd} || goto initrd
boot
"""


_from_hd_template = """#!ipxe

echo Boot from local disk {disk_number}
sanboot --no-describe --drive 0x8{disk_number}
"""


class IPXEPacker(packers.JSONPacker):

    def pack(self, obj: models.Netboot):
        boot = nc.BootAlternative[obj.boot]

        if boot == nc.BootAlternative.network:
            return _from_net_template.format(
                gc_host=obj.gc_host,
                gc_port=obj.gc_port,
                kernel=obj.kernel,
                initrd=obj.initrd,
            )
        elif boot.boot_type == "hd":
            return _from_hd_template.format(disk_number=boot.value[2])

        raise ValueError(f"Invalid boot alternative: {boot}")
