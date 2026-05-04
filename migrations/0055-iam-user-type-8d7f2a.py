# Copyright 2026 Genesis Corporation
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

import uuid as sys_uuid
from restalchemy.storage.sql import migrations

NS_UUID = sys_uuid.UUID("dfd0c604-607f-4260-981f-374f88435ea0")
EXORDOS_CORE_ORG_UUID = "11111111-1111-1111-1111-111111111111"
OWNER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000002"

SERVICE_TOKEN_PERMISSIONS = (
    ("iam.service_token.create", "Create service account tokens"),
)


def _u(name: str) -> str:
    return str(sys_uuid.uuid5(NS_UUID, name))


class MigrationStep(migrations.AbstractMigrationStep):
    def __init__(self):
        self._depends = [
            "0054-iam-idp-callback-kind-3a6c1b.py",
        ]

    @property
    def migration_id(self):
        return "8d7f2a9b-4c5d-4e8f-9a1b-2c3d4e5f6a7b"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        for name, description in SERVICE_TOKEN_PERMISSIONS:
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
        for name, _ in SERVICE_TOKEN_PERMISSIONS:
            session.execute(f"""
                INSERT INTO iam_binding_permissions (
                    uuid, role, permission, project_id
                ) VALUES (
                    gen_random_uuid(),
                    '{OWNER_ROLE_UUID}',
                    '{_u(name)}',
                    NULL
                );
            """)

    def upgrade(self, session):
        # Create user type enum and column
        expressions = [
            """
                DO $$ BEGIN
                    CREATE TYPE user_type_enum AS ENUM ('user', 'service');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """,
            """
                ALTER TABLE "iam_users"
                    ADD COLUMN IF NOT EXISTS "type" user_type_enum NOT NULL DEFAULT 'user';
            """,
        ]

        for expression in expressions:
            session.execute(expression)

        # Create service token permissions and bindings
        self._create_permissions(session)
        self._create_bindings(session)

    def _delete_bindings(self, session):
        for name, _ in SERVICE_TOKEN_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_binding_permissions
                WHERE
                    permission = '{_u(name)}';
            """)

    def _delete_permissions(self, session):
        for name, _ in SERVICE_TOKEN_PERMISSIONS:
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{_u(name)}';
            """)

    def downgrade(self, session):
        # Delete service token permissions and bindings first
        self._delete_bindings(session)
        self._delete_permissions(session)

        # Then drop user type column and enum
        expressions = [
            """
                ALTER TABLE "iam_users"
                    DROP COLUMN IF EXISTS "type";
            """,
            """
                DROP TYPE IF EXISTS user_type_enum;
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
