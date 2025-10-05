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

import logging
import time
import typing as tp
import uuid as sys_uuid
from xml.dom import minidom
import contextlib as ctxlib

import libvirt
import netaddr

from genesis_core.compute.dm import models
from genesis_core.common import constants as c
from genesis_core.compute import constants as nc
from genesis_core.compute.machine.pool.driver import base
from genesis_core.compute.machine.pool.driver import exceptions as pool_exc

ImageFormatType = tp.Literal["raw", "qcow2"]
NetworkType = tp.Literal["bridge", "network"]

META_TAG = "genesis:genesis"
META_CPU_TAG = "genesis:vcpu"
META_MEM_TAG = "genesis:mem"

LOG = logging.getLogger(__name__)


volume_template = """
<volume>
  <name>{name}</name>
  <capacity>{size}</capacity>
  <allocation>0</allocation>
</volume>
"""


volume_template_with_format = """
<volume>
  <name>{name}</name>
  <capacity>{size}</capacity>
  <allocation>0</allocation>
  <target>
    <format type="{format}"/>
  </target>
</volume>
"""


domain_template = """
<domain type="kvm">
  <metadata>
    <genesis:genesis xmlns:genesis="https://github.com/infraguys">
    </genesis:genesis>
  </metadata>
  <os>
    <type arch="x86_64" machine="q35">hvm</type>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state="off"/>
  </features>
  <cpu mode="host-passthrough"/>
  <clock offset="utc">
    <timer name="rtc" tickpolicy="catchup"/>
    <timer name="pit" tickpolicy="delay"/>
    <timer name="hpet" present="no"/>
  </clock>
  <pm>
    <suspend-to-mem enabled="no"/>
    <suspend-to-disk enabled="no"/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <controller type="usb" model="qemu-xhci" ports="5"/>
    <controller type="pci" model="pcie-root"/>
    <controller type="pci" model="pcie-root-port"/>
    <console type="pty"/>
    <channel type="unix">
      <source mode="bind"/>
      <target type="virtio" name="org.qemu.guest_agent.0"/>
    </channel>
    <channel type="spicevmc">
      <target type="virtio" name="com.redhat.spice.0"/>
    </channel>
    <input type="tablet" bus="usb"/>
    <graphics type="spice" port="-1" tlsPort="-1" autoport="yes">
      <image compression="off"/>
    </graphics>
    <video>
      <model type="qxl"/>
    </video>
    <redirdev bus="usb" type="spicevmc"/>
    <memballoon model="virtio"/>
    <rng model="virtio">
      <backend model="random">/dev/urandom</backend>
    </rng>
  </devices>
</domain>
"""


class XMLLibvirtMixin:

    @classmethod
    def add_element(
        cls,
        document: minidom.Document,
        tag_name: str,
        parent: minidom.Element | None = None,
        text: str | None = None,
        **kwargs,
    ) -> None:
        root = parent or document.firstChild
        element = document.createElement(tag_name)

        for name, value in kwargs.items():
            element.setAttribute(name, value)

        if text is not None:
            text_node = document.createTextNode(text)
            element.appendChild(text_node)

        root.appendChild(element)

    @classmethod
    def document_set_tag(
        cls,
        docement: minidom.Document,
        tag_name: str,
        text: str | None = None,
        meta_tag: str | None = None,
        parent: minidom.Element | None = None,
        **kwargs,
    ) -> None:
        root = parent or docement.firstChild
        # Firstly we need to remove the old value
        for node in root.getElementsByTagName(tag_name):
            root.removeChild(node)

        # Also we need to remove the old value from the meta
        if meta_tag is not None:
            meta_node = docement.getElementsByTagName(META_TAG)[0]
            for node in docement.getElementsByTagName(meta_tag):
                meta_node.removeChild(node)

            # Add the new value
            cls.add_element(docement, meta_tag, parent=meta_node, text=text)

        # Set the new value
        cls.add_element(docement, tag_name, parent=root, text=text, **kwargs)


class XMLLibvirtVolume(XMLLibvirtMixin):

    def __init__(self, volume: libvirt.virStorageVol | str):
        if isinstance(volume, libvirt.virStorageVol):
            self._volume = minidom.parseString(volume.XMLDesc())
        else:
            self._volume = minidom.parseString(volume)

    @property
    def xml(self) -> str:
        return self._volume.toxml()

    @classmethod
    def xml_from_base_template(
        cls, pool: libvirt.virStoragePool, name: str, size: int
    ) -> str:
        pool_type = (
            minidom.parseString(pool.XMLDesc())
            .firstChild.attributes["type"]
            .value
        )
        if pool_type == "zfs":
            return volume_template.format(name=name, size=size)

        return volume_template_with_format.format(
            name=f"{name}.qcow2", size=size, format="qcow2"
        )


class XMLLibvirtInstance(XMLLibvirtMixin):

    def __init__(self, domain: libvirt.virDomain | str):
        if isinstance(domain, libvirt.virDomain):
            self._domain = minidom.parseString(domain.XMLDesc())
        else:
            self._domain = minidom.parseString(domain)

    @property
    def xml(self) -> str:
        return self._domain.toxml()

    @classmethod
    def domain_set_name(cls, domain: minidom.Document, name: str) -> None:
        cls.document_set_tag(domain, "name", text=name)

    @classmethod
    def domain_set_uuid(
        cls, domain: minidom.Document, uuid: sys_uuid.UUID
    ) -> None:
        cls.document_set_tag(domain, "uuid", text=str(uuid))

    @classmethod
    def domain_set_vcpu(cls, domain: minidom.Document, cores: int) -> None:
        cls.document_set_tag(
            domain,
            "vcpu",
            text=str(cores),
            meta_tag=META_CPU_TAG,
            placement="static",
        )

    @classmethod
    def domain_set_memory(cls, domain: minidom.Document, memory: int) -> None:
        cls.document_set_tag(
            domain,
            "memory",
            text=str(memory),
            meta_tag=META_MEM_TAG,
            unit="MiB",
        )
        cls.document_set_tag(
            domain,
            "currentMemory",
            text=str(memory),
            unit="MiB",
        )

    @classmethod
    def domain_set_boot(
        cls, domain: minidom.Document, boot: nc.BootType
    ) -> None:
        os_element = domain.getElementsByTagName("os")[0]

        # TODO(akremenetsky): Fix this durty hack
        # cls.document_set_tag(domain, "boot", parent=os_element, dev=boot)
        cls.add_element(domain, "boot", parent=os_element, dev="network")
        cls.add_element(domain, "boot", parent=os_element, dev="hd")

    @classmethod
    def domain_add_disk(
        cls,
        domain: minidom.Document,
        image_path: str,
        device: str = "vda",
        bus: str = "virtio",
    ) -> None:
        if image_path.startswith("/dev/zvol/"):
            base_xml = "<disk type='block' device='disk'></disk>"
            image_format = "raw"
            document = minidom.parseString(base_xml)
            cls.document_set_tag(document, "source", dev=image_path)
        else:
            base_xml = "<disk type='file' device='disk'></disk>"
            image_format = "qcow2"
            document = minidom.parseString(base_xml)
            cls.document_set_tag(document, "source", file=image_path)

        cls.document_set_tag(document, "target", dev=device, bus=bus)
        cls.document_set_tag(
            document,
            "driver",
            name="qemu",
            type=image_format,
            discard="unmap",  # Support trimming of unused blocks
        )

        device_element = domain.getElementsByTagName("devices")[0]
        device_element.appendChild(document.firstChild)

    @classmethod
    def domain_add_interface(
        cls,
        domain: minidom.Document,
        iface_type: NetworkType = "network",
        source: str | None = None,
        model: str = "virtio",
        mtu: int = 1450,
        mac: str | None = None,
        rom: str | None = None,
    ) -> None:
        base_xml = "<interface type='{iface_type}'></interface>".format(
            iface_type=iface_type
        )
        document = minidom.parseString(base_xml)
        cls.document_set_tag(document, "model", type=model)
        cls.document_set_tag(document, "mtu", size=str(mtu))
        if rom is not None:
            cls.document_set_tag(document, "rom", bar="on", file=rom)

        mac_address = mac or models.Port.generate_mac()
        cls.document_set_tag(document, "mac", address=mac_address)

        if iface_type == "bridge":
            if source is None:
                raise ValueError("Source is required for bridge interface")
            cls.document_set_tag(document, "source", bridge=source)
        elif iface_type == "network":
            if source is None:
                raise ValueError("Source is required for network interface")
            cls.document_set_tag(document, "source", network=source)
        else:
            raise ValueError(f"Unsupported interface type: {iface_type}")

        device_element = domain.getElementsByTagName("devices")[0]
        device_element.appendChild(document.firstChild)

    def set_name(self, name: str) -> None:
        return self.domain_set_name(self._domain, name)

    def set_uuid(self, uuid: sys_uuid.UUID) -> None:
        return self.domain_set_uuid(self._domain, uuid)

    def set_vcpu(self, cores: int) -> None:
        return self.domain_set_vcpu(self._domain, cores)

    def set_memory(self, memory: int) -> None:
        return self.domain_set_memory(self._domain, memory)

    def set_boot(self, boot: nc.BootType) -> None:
        return self.domain_set_boot(self._domain, boot)

    def add_disk(
        self,
        image_path: str,
        device: str = "vda",
        bus: str = "virtio",
    ) -> None:
        return self.domain_add_disk(self._domain, image_path, device, bus)

    def add_interface(
        self,
        iface_type: NetworkType = "network",
        source: str | None = None,
        model: str = "virtio",
        mtu: int = 1450,
        mac: str | None = None,
        rom: str | None = None,
    ) -> None:
        return self.domain_add_interface(
            self._domain,
            iface_type,
            source,
            model=model,
            rom=rom,
            mtu=mtu,
            mac=mac,
        )


class LibvirtPoolDriverSpec(tp.NamedTuple):
    driver: tp.Literal["libvirt"]
    network: str
    storage_pool: str
    connection_uri: str
    machine_prefix: str | None = None
    network_type: NetworkType = "network"
    iface_rom_file: str | None = None
    iface_mtu: int = 1450


class LibvirtPoolDriver(base.AbstractPoolDriver):

    def __init__(self, pool: models.MachinePool):
        self._spec = LibvirtPoolDriverSpec(**pool.driver_spec)
        self._pool = pool
        # Check if connection string is valid and we can connect
        _ = self._client

    @property
    def _client(self):
        instance = getattr(self, "_client_instance", None)
        # isAlive() doesn't actually ping host (so it's cheap),
        #  but it will return 0 if there were any errors before
        if not instance or not instance.isAlive():
            instance = libvirt.open(self._spec.connection_uri)
            if not instance:
                raise ConnectionError(
                    f"Failed to open libvirt connection: {self._spec.connection_uri}"
                )
            self._client_instance = instance
        return instance

    @staticmethod
    def _eq_memory(target_memory: int, actual_memory: int) -> bool:
        return abs(target_memory - actual_memory) <= 0.09 * actual_memory

    def _create_domain(self, domain_xml: str) -> libvirt.virDomain:
        virt_domain = self._client.defineXML(domain_xml)
        virt_domain.create()

        # Set the autostart flag to run the domain
        # after hypervisor restart
        virt_domain.setAutostart(True)

        return virt_domain

    def _domain2machine_name(self, name: str) -> str:
        machine_prefix_len = len(self._spec.machine_prefix or "")
        uuid_prefix_len = 9
        return name[machine_prefix_len + uuid_prefix_len :]

    def _machine2domain_name(self, machine: models.Machine) -> str:
        machine_prefix = self._spec.machine_prefix or ""
        uuid_prefix = str(machine.uuid)[:8] + "-"
        return f"{machine_prefix}{uuid_prefix}{str(machine.name)}"

    def _domain2machine(self, domain: libvirt.virDomain) -> models.Machine:

        # Determine the number of cores and amount of memory directly
        # from the metadata.
        domain_xml = minidom.parseString(domain.XMLDesc())
        cores_xml = domain_xml.getElementsByTagName(META_CPU_TAG)[0]
        cores = int(cores_xml.firstChild.nodeValue)
        ram_xml = domain_xml.getElementsByTagName(META_MEM_TAG)[0]
        ram = int(ram_xml.firstChild.nodeValue)

        return models.Machine(
            uuid=sys_uuid.UUID(domain.UUIDString()),
            name=self._domain2machine_name(domain.name()),
            machine_type=nc.NodeType.VM.value,
            cores=cores,
            ram=ram,
            # These fields don't make sense for data plane entities
            status=nc.MachineStatus.IDLE.value,
            pool=self._pool.uuid,
            project_id=c.SERVICE_PROJECT_ID,
        )

    def _split_vir_volume_name(self, name: str) -> tp.Tuple[str, str | None]:
        name_without_format = name.split(".")[0]

        # The name doesn't contain machine UUID
        if "_" not in name_without_format:
            return sys_uuid.UUID(name_without_format), None

        # The name contains machine UUID and volume UUID
        volume_uuid, machine_uuid = (
            sys_uuid.UUID(u) for u in name_without_format.split("_")
        )
        return volume_uuid, machine_uuid

    def _form_vir_volume_name(self, volume: models.MachineVolume) -> str:
        return (
            f"{str(volume.uuid)}_{str(volume.machine)}"
            if volume.machine
            else f"{str(volume.uuid)}"
        )

    def _vir_volume2machine_volume(
        self, volume: libvirt.virStorageVol
    ) -> models.MachineVolume:
        volume_uuid, machine_uuid = self._split_vir_volume_name(volume.name())
        info = volume.info()
        LOG.debug("Volume info: %s", info)

        return models.MachineVolume(
            uuid=volume_uuid,
            machine=machine_uuid,
            path=volume.path(),
            size=15,
            project_id=c.SERVICE_PROJECT_ID,
        )

    def _list_interfaces(self, machine: models.Machine) -> list[models.Port]:
        """List all interfaces of the machine."""
        # TODO(akremenetsky): The `Port` model is used to represent
        # an interface. We need more appropriate model.
        ports = []

        domain = self._client.lookupByUUIDString(str(machine.uuid))
        domain_xml = minidom.parseString(domain.XMLDesc())

        for iface in domain_xml.getElementsByTagName("interface"):
            mac_tags = iface.getElementsByTagName("mac")
            if len(mac_tags) != 1 or not mac_tags[0].getAttribute("address"):
                LOG.error("Unable to detect MAC address for %s", iface)
                continue

            mac = mac_tags[0].getAttribute("address")
            ports.append(
                models.Port(
                    uuid=sys_uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    machine=machine.uuid,
                    mac=mac,
                    project_id=c.SERVICE_PROJECT_ID,
                )
            )

        return ports

    def list_volumes(
        self, machine: models.Machine
    ) -> tp.Iterable[models.MachineVolume]:
        storage_pool = self._client.storagePoolLookupByName(
            self._spec.storage_pool
        )
        volumes = []
        for v in storage_pool.listAllVolumes():
            try:
                volumes.append(self._vir_volume2machine_volume(v))
            except Exception:
                LOG.warning("Failed to parse volume %s", v.name())

        result = [v for v in volumes if v.machine == machine.uuid]
        LOG.debug("Volumes: %s", result)
        return result

    def get_volume(
        self, machine: sys_uuid.UUID, uuid: sys_uuid.UUID
    ) -> models.MachineVolume:
        target_volume = models.MachineVolume(
            uuid=uuid,
            machine=machine,
            # These fields don't make sense in this case, just placeholders
            size=1,
            node=sys_uuid.uuid4(),
            project_id=c.SERVICE_PROJECT_ID,
        )
        name = self._form_vir_volume_name(target_volume)

        """Get the machine volume by uuid."""
        storage_pool = self._client.storagePoolLookupByName(
            self._spec.storage_pool
        )

        # We don't know which format is used for the volume so we try them all
        for fmt in tp.get_args(ImageFormatType):
            name_with_format = f"{name}.{fmt}"
            try:
                volume = storage_pool.storageVolLookupByName(name_with_format)
                break
            except libvirt.libvirtError as e:
                if e.get_error_code() == libvirt.VIR_ERR_NO_STORAGE_VOL:
                    continue
                raise
        else:
            raise pool_exc.VolumeNotFoundError(volume=uuid)

        return self._vir_volume2machine_volume(volume)

    def create_volume(
        self, volume: models.MachineVolume
    ) -> models.MachineVolume:
        storage_pool = self._client.storagePoolLookupByName(
            self._spec.storage_pool
        )
        name = self._form_vir_volume_name(volume)
        volume_xml = XMLLibvirtVolume.xml_from_base_template(
            storage_pool, name, volume.size << 30
        )

        try:
            virt_volume = storage_pool.createXML(volume_xml)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_STORAGE_VOL_EXIST:
                raise pool_exc.VolumeAlreadyExistsError(volume=volume.uuid)
            raise

        # TODO(akremenetsky): We shouldn't change the original object
        volume.path = virt_volume.path()

        LOG.debug("The volume %s has been created", name)
        return volume

    def delete_volume(self, volume: models.MachineVolume) -> None:
        try:
            v = self._client.storageVolLookupByPath(volume.path)
        except libvirt.libvirtError as e:
            LOG.exception("The volume %s has not been found:", volume.uuid)
            return

        try:
            v.wipe()
        except libvirt.libvirtError as e:
            # Some backends don't need wiping, for ex. ZFS
            if e.get_error_code() != 3:  # VIR_ERR_NO_SUPPORT
                raise
        max_iters = 20
        for i in range(max_iters + 1):
            try:
                v.delete()
            except libvirt.libvirtError as e:
                if i == max_iters:
                    raise
                # Volume may be busy, just wait a little bit
                time.sleep(0.05)
            else:
                break
        LOG.debug("The volume %s has been deleted", v.name())
        return

    def list_machines(self) -> tp.List[models.Machine]:
        """Return machine list from data plane."""
        domains = self._client.listAllDomains()

        # If the filter prefix is not set, return all domains
        if not self._spec.machine_prefix:
            machines = [self._domain2machine(d) for d in domains]
            LOG.debug("Machines: %s", machines)
            return machines

        # Otherwise, filter domains by the prefix
        machines = []
        for d in domains:
            if d.name().startswith(self._spec.machine_prefix):
                machines.append(self._domain2machine(d))

        LOG.debug("Machines: %s", machines)
        return machines

    def create_machine(
        self,
        machine: models.Machine,
        volumes: tp.Iterable[models.MachineVolume],
        ports: tp.Iterable[models.Port],
    ) -> models.Machine:
        """Create a new LibVirt domain."""
        domain = XMLLibvirtInstance(domain_template)

        # Set base characteristics for the domain
        domain.set_uuid(machine.uuid)
        domain.set_name(self._machine2domain_name(machine))
        domain.set_vcpu(machine.cores)
        domain.set_memory(machine.ram)
        domain.set_boot(nc.BootAlternative[machine.boot].boot_type)

        for port in ports:
            domain.add_interface(
                mac=port.mac,
                rom=self._spec.iface_rom_file,
                mtu=self._spec.iface_mtu,
                # TODO(akremenetsky): This parameter should be taken from
                # the network
                iface_type=self._spec.network_type,
                source=self._spec.network,
            )

        # Add the volumes to the domain
        for i, volume in enumerate(volumes):
            if volume.path is None:
                raise ValueError(f"Volume {volume.uuid} has no path")

            domain.add_disk(
                image_path=volume.path,
                device="vd" + chr(ord("a") + i),
                bus="virtio",
            )

        # Create the domain from the XML specification
        domain_spec = domain.xml
        self._create_domain(domain_spec)

        LOG.debug(
            "The domain %s has been created\nDomain spec:\n%s",
            machine.uuid,
            domain_spec,
        )
        return machine

    def delete_machine(
        self, machine: models.Machine, delete_volumes: bool = True
    ) -> None:
        """
        Delete a machine from the data plane.

        :param machine: The machine to delete
        """
        domain = self._client.lookupByUUIDString(str(machine.uuid))

        # Remove the libvirt domain
        try:
            domain.destroy()
        except libvirt.libvirtError:
            LOG.debug("The domain is not in the running state")
        # FIXME(akremenetsky): Actully we should undefine the
        # domain before volume deletion
        domain.undefine()

        if delete_volumes:
            for volume in self.list_volumes(machine):
                self.delete_volume(volume)

        LOG.debug("The domain %s has been destroyed", machine.uuid)

    def set_machine_cores(self, machine: models.Machine, cores: int) -> None:
        """Set machine cores."""
        ports = self._list_interfaces(machine)
        volumes = self.list_volumes(machine)
        self.delete_machine(machine, delete_volumes=False)

        machine.cores = cores
        self.create_machine(machine, volumes=volumes, ports=ports)
        LOG.debug(
            "The domain %s was updated with cores %s", machine.uuid, cores
        )

    def set_machine_ram(self, machine: models.Machine, ram: int) -> None:
        """Set machine ram."""
        ports = self._list_interfaces(machine)
        volumes = self.list_volumes(machine)
        self.delete_machine(machine, delete_volumes=False)

        machine.ram = ram
        self.create_machine(machine, volumes=volumes, ports=ports)
        LOG.debug("The domain %s was updated with ram %s", machine.uuid, ram)

    def reset_machine(self, machine: models.Machine) -> None:
        """Reset the machine."""
        domain = self._client.lookupByUUIDString(str(machine.uuid))

        try:
            domain.destroy()
        except libvirt.libvirtError:
            LOG.debug("The domain is not in the running state")

        domain.create()
        LOG.debug("The domain %s was reset", str(machine.uuid))
