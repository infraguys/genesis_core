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

import uuid as sys_uuid
from restalchemy.storage.sql import migrations

NS_UUID = sys_uuid.UUID("dfd0c604-607f-4260-981f-374f88435ea0")
GENESIS_CORE_ORG_UUID = "11111111-1111-1111-1111-111111111111"
OWNER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000002"

# Network LB permissions
NETWORK_LB_PERMISSIONS = (
    # Network
    ("network.lb.read", "List and read load balancers"),
    ("network.lb.create", "Create load balancers"),
    ("network.lb.update", "Update load balancers"),
    ("network.lb.delete", "Delete load balancers"),
    ("network.lb_vhost.read", "List and read LB virtual hosts"),
    ("network.lb_vhost.create", "Create LB virtual hosts"),
    ("network.lb_vhost.update", "Update LB virtual hosts"),
    ("network.lb_vhost.delete", "Delete LB virtual hosts"),
    ("network.lb_vhost_route.read", "List and read LB vhost routes"),
    ("network.lb_vhost_route.create", "Create LB vhost routes"),
    ("network.lb_vhost_route.update", "Update LB vhost routes"),
    ("network.lb_vhost_route.delete", "Delete LB vhost routes"),
    ("network.lb_backendpool.read", "List and read LB backend pools"),
    ("network.lb_backendpool.create", "Create LB backend pools"),
    ("network.lb_backendpool.update", "Update LB backend pools"),
    ("network.lb_backendpool.delete", "Delete LB backend pools"),
    # Compute
    ("compute.node.get_private_key", "Get node(s) agent private key"),
    ("compute.node_set.get_private_key", "Get node(s) agent private key"),
    # Config
    ("config.config.read", "List and read configs"),
    ("config.config.create", "Create configs"),
    ("config.config.update", "Update configs"),
    ("config.config.delete", "Delete configs"),
    # Services
    ("em.service.read", "List and read services"),
    ("em.service.create", "Create services"),
    ("em.service.update", "Update services"),
    ("em.service.delete", "Delete services"),
)


def _u(name: str) -> str:
    return str(sys_uuid.uuid5(NS_UUID, name))


COMPUTE_PROJECT_UUID = _u("GenesisCore-Compute-Project")


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0052-iam-user-custom-props-bc80b5.py"]

    @property
    def migration_id(self):
        return "11c9a8bc-cc22-42d1-a8f8-cbfa21707fce"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        for name, description in NETWORK_LB_PERMISSIONS:
            session.execute(f"""
                INSERT INTO iam_permissions (
                    uuid, name, description
                ) VALUES (
                    '{_u(name)}',
                    '{name}',
                    '{description}'
                )
                ON CONFLICT (uuid) DO NOTHING;
            """)

    def _create_bindings(self, session):
        for name, _ in NETWORK_LB_PERMISSIONS:
            session.execute(f"""
                INSERT INTO iam_binding_permissions (
                    uuid, role, permission, project_id
                ) VALUES (
                    '{_u("binding." + name)}',
                    '{OWNER_ROLE_UUID}',
                    '{_u(name)}',
                    '{COMPUTE_PROJECT_UUID}'
                );
            """)

    def upgrade(self, session):
        self._create_permissions(session)
        self._create_bindings(session)

    def _delete_bindings(self, session):
        for name, _ in NETWORK_LB_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_binding_permissions
                WHERE
                    permission = '{_u(name)}';
            """)

    def _delete_permissions(self, session):
        for name, _ in NETWORK_LB_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """)

    def downgrade(self, session):
        self._delete_bindings(session)
        self._delete_permissions(session)


migration_step = MigrationStep()
