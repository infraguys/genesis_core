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

import typing as tp

from genesis_core.node.dm import models


DHCP_ISC_SVC_NAME = "isc-dhcp-server.service"


_common_settings = """# Common settings
allow bootp;
allow booting;
option ip-forwarding false;
option mask-supplier false;
max-lease-time 1209600;
default-lease-time 1209600;
log-facility local7;
"""


_netboot_template = """

	# Netboot
	if substring (option vendor-class-identifier, 15, 5) = "00007" {{
		filename "uefi/ipxe.efi";
	}} else {{
		filename "bios/undionly.kpxe";
	}}
	next-server {next_server};
"""

_auto_discovery_pool_template = """
	pool {{
		max-lease-time 900;
		default-lease-time 900;

		range {start_ip} {end_ip};
	}}
"""


_host_template = """
	host {hostname} {{
		hardware ethernet {mac_address};
		fixed-address {ip_address};
	}}"""


_subnet_template = """
subnet {net_address} netmask {net_mask} {{
	option domain-name-servers {dns_servers};
	option routers {routers};
	{pool}
	{hosts}
	{netboot}
}}
"""


def dhcp_config(subnets: tp.Dict[models.Subnet, tp.List[models.Port]]) -> str:
    # FIXME(akremenetsky): It's considered the subnets aren't intersecting

    config = _common_settings

    # Build every subnet
    for subnet, ports in subnets.items():

        # TODO(akremenetsky): Add pool when auto-discovery is enabled
        # for baremetal discovery
        pool = ""

        hosts = ""
        for port in ports:
            if port.mac is None or port.ipv4 is None:
                raise ValueError("Port is not configured")

            hosts += _host_template.format(
                mac_address=port.mac,
                ip_address=port.ipv4,
                hostname=f"P_{str(port.uuid)}",
            )

        netboot = _netboot_template.format(next_server=subnet.next_server)
        dns_servers = ",".join(subnet.dns_servers)
        routers = ",".join(subnet.routers)

        config += _subnet_template.format(
            net_address=str(subnet.cidr.network),
            net_mask=str(subnet.cidr.netmask),
            dns_servers=dns_servers,
            routers=routers,
            pool=pool,
            hosts=hosts,
            netboot=netboot,
        )

    return config
