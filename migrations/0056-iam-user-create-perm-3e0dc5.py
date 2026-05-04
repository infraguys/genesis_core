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

# IAM user permissions
IAM_USER_PERMISSIONS = (("iam.user.create", "Create IAM users"),)


def _u(name: str) -> str:
    return str(sys_uuid.uuid5(NS_UUID, name))


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0055-iam-user-type-8d7f2a.py"]

    @property
    def migration_id(self):
        return "3e0dc5dd-1d40-444c-ae03-4817da87b0bc"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        for name, description in IAM_USER_PERMISSIONS:
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

    def upgrade(self, session):
        self._create_permissions(session)

    def _delete_bindings(self, session):
        for name, _ in IAM_USER_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_binding_permissions
                WHERE permission = '{_u(name)}';
            """)

    def _delete_permissions(self, session):
        for name, _ in IAM_USER_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """)

    def downgrade(self, session):
        self._delete_bindings(session)
        self._delete_permissions(session)
        for name, _ in IAM_USER_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """)


migration_step = MigrationStep()
