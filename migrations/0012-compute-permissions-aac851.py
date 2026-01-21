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

COMPUTE_NODE_DEF_PERMISSIONS = (
    ("compute.node.read", "List and read own nodes"),
    ("compute.node.create", "Create own nodes"),
    ("compute.node.update", "Update own nodes"),
    ("compute.node.delete", "Delete own nodes"),
)


def _u(name: str) -> str:
    return str(sys_uuid.uuid5(NS_UUID, name))


COMPUTE_PROJECT_UUID = _u("GenesisCore-Compute-Project")


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0011-add-surname-and-phone-ea974b.py"]

    @property
    def migration_id(self):
        return "aac8510e-9a0d-4db5-9a94-7bc8abff40e1"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        for name, description in COMPUTE_NODE_DEF_PERMISSIONS:
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

    def _create_project(self, session):
        session.execute(f"""
            INSERT INTO iam_projects (
                uuid, name, description, organization
            ) VALUES (
                '{COMPUTE_PROJECT_UUID}',
                'compute-core',
                'Comptue and Baremetal Core Project',
                '{GENESIS_CORE_ORG_UUID}'
            )
            ON CONFLICT (uuid) DO NOTHING;
        """)

    def _create_bindings(self, session):
        for name, _ in COMPUTE_NODE_DEF_PERMISSIONS:
            session.execute(f"""
                INSERT INTO iam_binding_permissions (
                    uuid, role, permission, project_id
                ) VALUES (
                    gen_random_uuid(),
                    '{OWNER_ROLE_UUID}',
                    '{_u(name)}',
                    '{COMPUTE_PROJECT_UUID}'
                );
            """)

    def upgrade(self, session):
        self._create_permissions(session)
        self._create_project(session)
        self._create_bindings(session)

    def _delete_bindings(self, session):
        for name, _ in COMPUTE_NODE_DEF_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_binding_permissions
                WHERE
                    permission = '{_u(name)}';
            """)

    def _delete_project(self, session):
        session.execute(f"""
            DELETE FROM iam_projects
            WHERE uuid = '{COMPUTE_PROJECT_UUID}';
        """)

    def _delete_permissions(self, session):
        for name, _ in COMPUTE_NODE_DEF_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """)

    def downgrade(self, session):
        self._delete_bindings(session)
        self._delete_project(session)
        self._delete_permissions(session)


migration_step = MigrationStep()
