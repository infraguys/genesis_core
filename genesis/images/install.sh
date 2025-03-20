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

# Install packages
sudo apt update
sudo apt install build-essential python3.12-dev python3.12-venv postgresql \
    libev-dev libvirt-dev tftpd-hpa isc-dhcp-server -y

# Configure netboot
sudo cp "$GC_ART_DIR/dhcpd.conf" /etc/dhcp/dhcpd.conf
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
sudo cp "$GC_PATH/scripts/bootstrap.sh" $BOOTSTRAP_PATH/0100-gc-bootstrap.sh
python3 -m uuid | sudo tee /var/lib/genesis/node-id

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH"/.venv/bin/activate
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# Apply migrations
ra-apply-migration --config-dir "$GC_PATH/etc/genesis_core/" --path "$GC_PATH/migrations"
deactivate

# Create links to venv
sudo ln -sf "$VENV_PATH/bin/gc-user-api" "/usr/bin/gc-user-api"
sudo ln -sf "$VENV_PATH/bin/gc-orch-api" "/usr/bin/gc-orch-api"
sudo ln -sf "$VENV_PATH/bin/gc-gservice" "/usr/bin/gc-gservice"
sudo ln -sf "$VENV_PATH/bin/gc-bootstrap" "/usr/bin/gc-bootstrap"

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/gc-user-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/gc-orch-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/gc-gservice.service" $SYSTEMD_SERVICE_DIR

# Enable genesis core services
sudo systemctl enable gc-user-api gc-orch-api gc-gservice
