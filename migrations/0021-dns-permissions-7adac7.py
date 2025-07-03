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

DNS_NODE_DEF_PERMISSIONS = (
    ("dns.domain.read", "List and read own domains"),
    ("dns.domain.create", "Create own domains"),
    ("dns.domain.update", "Update own domains"),
    ("dns.domain.delete", "Delete own domains"),
    ("dns.record.read", "List and read own records"),
    ("dns.record.create", "Create own records"),
    ("dns.record.update", "Update own records"),
    ("dns.record.delete", "Delete own records"),
)


def _u(name: str) -> str:
    return str(sys_uuid.uuid5(NS_UUID, name))


DNS_PROJECT_UUID = _u("GenesisCore-Dns-Project")


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0020-init-secret-a643b1.py"]

    @property
    def migration_id(self):
        return "7adac7d0-3d20-4c09-a6f5-f90f4442a5d4"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        for name, description in DNS_NODE_DEF_PERMISSIONS:
            session.execute(
                f"""
                INSERT INTO iam_permissions (
                    uuid, name, description
                ) VALUES (
                    '{_u(name)}',
                    '{name}',
                    '{description}'
                )
                ON CONFLICT (uuid) DO NOTHING;
            """
            )

    def _create_project(self, session):
        session.execute(
            f"""
            INSERT INTO iam_projects (
                uuid, name, description, organization
            ) VALUES (
                '{DNS_PROJECT_UUID}',
                'dns-core',
                'Dns Core Project',
                '{GENESIS_CORE_ORG_UUID}'
            )
            ON CONFLICT (uuid) DO NOTHING;
        """
        )

    def _create_bindings(self, session):
        for name, _ in DNS_NODE_DEF_PERMISSIONS:
            session.execute(
                f"""
                INSERT INTO iam_binding_permissions (
                    uuid, role, permission, project_id
                ) VALUES (
                    gen_random_uuid(),
                    '{OWNER_ROLE_UUID}',
                    '{_u(name)}',
                    '{DNS_PROJECT_UUID}'
                );
            """
            )

    def upgrade(self, session):
        self._create_permissions(session)
        self._create_project(session)
        self._create_bindings(session)

    def _delete_bindings(self, session):
        for name, _ in DNS_NODE_DEF_PERMISSIONS:
            session.execute(
                f"""
                DELETE FROM iam_binding_permissions
                WHERE
                    permission = '{_u(name)}';
            """
            )

    def _delete_project(self, session):
        session.execute(
            f"""
            DELETE FROM iam_projects
            WHERE uuid = '{DNS_PROJECT_UUID}';
        """
        )

    def _delete_permissions(self, session):
        for name, _ in DNS_NODE_DEF_PERMISSIONS:
            session.execute(
                f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """
            )

    def downgrade(self, session):
        self._delete_bindings(session)
        self._delete_project(session)
        self._delete_permissions(session)


migration_step = MigrationStep()
