# Basic usage

This guide describes how to install and use Genesis Core on existing infrastructure. The existing infrastructure can be a local machine or several servers.
It's assumed Linux(Ubuntu) is used as the OS on your machines.

## Requirements

Before you install and use genesis core you need to install several requirements:

### Packages

Install necessary packages:

#### Ubuntu

Install packages

```bash
sudo apt update
sudo apt install qemu-kvm qemu-utils libvirt-daemon-system libvirt-dev mkisofs -y
```

Add user to group

```bash
sudo adduser $USER libvirt
sudo adduser $USER kvm
```

### Libvirt

Create a libvirt storage pool or use `default` if it already exists.

Check pools:

```bash
sudo virsh pool-list --all
```

Create a new pool if no one exists or you would like to use another one.

```bash
sudo virsh pool-define-as default dir --target "/var/lib/libvirt/images/"
sudo virsh pool-build default
sudo virsh pool-start default
sudo virsh pool-autostart default
```

Check the status with virsh-info:

```bash
sudo virsh pool-info default
```

## Installation

The simplest way to install Genesis Core is to get a prebuilt virtual machine image with all necessary dependencies. Take the the [latest image here](http://repository.genesis-core.tech:8081/genesis-core/latest/genesis-core.qcow2).

### Local machine / Development

Install Genesis DevTools first. For more information about it, see [Genesis DevTools](https://github.com/infraguys/genesis_devtools). The devtools allows to build and run the genesis core locally. Since we already downloaded the latest image, we don't need to build it from scratch but if you need to build an image from source look at the [instructions here](https://github.com/infraguys/genesis_devtools?tab=readme-ov-file#build).

The devtools has `bootstrap` command that will start the Genesis Core locally.

```bash
genesis bootstrap -i genesis-core.raw -m core
```

For more information about the `bootstrap` command, see [instructions here](https://github.com/infraguys/genesis_devtools?tab=readme-ov-file#bootstrap).

The installation is ready at address `10.20.0.2` but at this time it's not very useful since it cannot run any workload. Let's add a local machine as a hypervisor to solve this problem.

#### Get admin token

Before we can add a hypervisor, we need to get an admin token. The command to get the token is:

```bash
curl --location 'http://10.20.0.2:11010/v1/iam/clients/00000000-0000-0000-0000-000000000000/actions/get_token/invoke' \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode 'grant_type=password' \
    --data-urlencode 'username=<YOUR_ADMIN_USERNAME>' \
    --data-urlencode 'password=<YOUR_ADMIN_PASSWORD>' \
    --data-urlencode 'client_id=GenesisCoreClientId' \
    --data-urlencode 'client_secret=GenesisCoreClientSecret' \
    --data-urlencode 'scope=' \
    --data-urlencode 'ttl=86400'
```

The return value is `json` object with the `access_token` field. Copy the token and use it in the next steps.

#### Add hypervisor

##### Libvirt via SSH (preffered)

Create key in genesis core's VM for root user:

```console
# ssh-keygen
```

Copy public key to hypervisor (recommended user is `ubuntu`)

##### Libvirt via TCP connect

We need to get access to libvirt via a tcp connection. By default the tcp connection is closed, so we need to enable it.

**NOTE:** For development purposes we can use raw tcp connection. Don't use it in production.

Edit libvirt configuration file `/etc/libvirt/libvirtd.conf`, add these lines;

```bash
listen_tcp = 1
listen_addr = "0.0.0.0"
auth_tcp = "none"
```

Run commands to enable libvirt tcp connection:

```bash
sudo systemctl stop libvirtd
sudo systemctl enable --now libvirtd-tcp.socket
sudo systemctl start libvirtd
```

Check the libvirt is listening the tcp socket:

```bash
sudo systemctl status libvirtd.service
sudo systemctl status libvirtd.service | grep "libvirtd-tcp.socket"
```

##### Configure ZFS for storage

It's recommended to create distinct dataset for zvols:

```bash
zpool create rpool ... # create pool itself
zfs create -o volmode=dev rpool/disks
virsh pool-define-as --name rpool --source-name rpool/disks --type zfs
virsh pool-start rpool
virsh pool-autostart rpool
```

##### Config hypervisor in core

Add the machine as a hypervisor, replace `XXXX` with the token from the previous step.:

```bash
curl --location --globoff 'http://10.20.0.2:11010/v1/compute/hypervisors/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer XXXX' \
--data '{
    "driver_spec": {
        "driver": "libvirt",
        "iface_mtu": 1500,
        "network_type": "network",
        "network": "genesis-core-net",
        "storage_pool": "default", // for qcow
        "storage_pool": "rpool", // for ZFS
        "connection_uri": "qemu+tcp://10.20.0.1/system", // for TCP connect
        "connection_uri": "qemu+ssh://ubuntu@10.20.0.1:22/system?no_verify=1", // for SSH connect
        "machine_prefix": "dev-"
    },
    "avail_cores": 4,
    "avail_ram": 4096,
    "all_cores": 4,
    "all_ram": 4096,
    "status": "ACTIVE"
}'
```

- storage_pool - name of the libvirt storage pool to use.
- connection_uri - libvirt connection uri. If you need to add another machine use different ip address.
- all_cores - total number of cores you would like to allocate to the hypervisor.
- all_ram - total amount of ram you would like to allocate to the hypervisor.
- avail_cores - use the same value as `all_cores`.
- avail_ram - use the same value as `all_ram`.

### Production

The production installation guide will be added soon.

## Usage

Follow the [usage guide](https://github.com/infraguys/genesis_core/wiki/Usage) for more information.
