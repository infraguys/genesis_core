#!/usr/bin/env bash

# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
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

set -eu
set -x
set -o pipefail

GC_PATH="/opt/genesis_core"
GC_CFG_DIR=/etc/genesis_core
GC_ART_DIR="$GC_PATH/artifacts"
VENV_PATH="$GC_PATH/.venv"
BOOTSTRAP_PATH="/var/lib/genesis/bootstrap/scripts"

GC_PG_USER="genesis_core"
GC_PG_PASS="genesis_core"
GC_PG_DB="genesis_core"

SYSTEMD_SERVICE_DIR=/etc/systemd/system/

DEV_SDK_PATH="/opt/gcl_sdk"
SDK_DEV_MODE=$([ -d "$DEV_SDK_PATH" ] && echo "true" || echo "false")

# Install packages
sudo apt update
sudo apt install postgresql libev-dev libvirt-dev \
    tftpd-hpa isc-dhcp-server -y

# Useful for all-in-one-vm tests
# sudo apt install qemu-kvm libvirt-daemon-system zfsutils-linux \
#     libvirt-daemon-driver-storage-zfs libvirt-clients -y
#
# # Add disk, create pool
# zpool create zfspool /dev/vdX
#
# # Just separate dataset for libvirt
# zfs create zfspool/disks
#
# # Add pool into libvirt
# virsh pool-define-as --name zfspool --source-name zfspool/disks --type zfs
# virsh pool-start zfspool


# Configure netboot
sudo mkdir -p /srv/tftp/bios
sudo cp "$GC_ART_DIR/undionly.kpxe" /srv/tftp/bios/undionly.kpxe
sudo cp "$GC_ART_DIR/initrd.img" /srv/tftp/bios/initrd.img
sudo cp "$GC_ART_DIR/vmlinuz" /srv/tftp/bios/vmlinuz

# Default creds for genesis core services
sudo -u postgres psql -c "CREATE ROLE $GC_PG_USER WITH LOGIN PASSWORD '$GC_PG_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $GC_PG_USER OWNER $GC_PG_DB;"

# Install genesis core
sudo mkdir -p $GC_CFG_DIR
sudo cp "$GC_PATH/etc/genesis_core/genesis_core.conf" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_core/logging.yaml" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_core/event_type_mapping.yaml" $GC_CFG_DIR/
sudo cp "$GC_PATH/genesis/images/startup_cfg.yaml" $GC_CFG_DIR/
sudo cp "$GC_PATH/genesis/images/bootstrap.sh" $BOOTSTRAP_PATH/0100-gc-bootstrap.sh

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH"/.venv/bin/activate
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# In the dev mode the gcl_sdk package is installed from the local machine
if [[ "$SDK_DEV_MODE" == "true" ]]; then
    pip uninstall -y gcl_sdk
    pip install -e "$DEV_SDK_PATH"
fi

# Configuration for universal agent
sudo cp -r "$GC_PATH/etc/genesis_universal_agent" /etc/

# Apply migrations
ra-apply-migration --config-dir "$GC_PATH/etc/genesis_core/" --path "$GC_PATH/migrations"
deactivate

# Create links to venv
sudo ln -sf "$VENV_PATH/bin/gc-user-api" "/usr/bin/gc-user-api"
sudo ln -sf "$VENV_PATH/bin/gc-orch-api" "/usr/bin/gc-orch-api"
sudo ln -sf "$VENV_PATH/bin/gc-status-api" "/usr/bin/gc-status-api"
sudo ln -sf "$VENV_PATH/bin/gc-gservice" "/usr/bin/gc-gservice"
sudo ln -sf "$VENV_PATH/bin/gc-bootstrap" "/usr/bin/gc-bootstrap"
sudo ln -sf "$VENV_PATH/bin/genesis-universal-agent" "/usr/bin/genesis-universal-agent"
sudo ln -sf "$VENV_PATH/bin/genesis-universal-scheduler" "/usr/bin/genesis-universal-scheduler"

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/gc-user-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/gc-orch-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/gc-status-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/gc-gservice.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-universal-agent.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-universal-scheduler.service" $SYSTEMD_SERVICE_DIR

# Enable genesis core services
sudo systemctl enable gc-user-api gc-orch-api gc-status-api gc-gservice \
    genesis-universal-agent \
    genesis-universal-scheduler


# Prepare DNSaaS

# Install packages
sudo apt install pdns-backend-pgsql pdns-server -y

sudo rm /etc/powerdns/pdns.d/bind.conf
sudo cp "$GC_PATH/etc/powerdns/genesis.conf" /etc/powerdns/pdns.d/genesis.conf

sudo systemctl enable pdns
