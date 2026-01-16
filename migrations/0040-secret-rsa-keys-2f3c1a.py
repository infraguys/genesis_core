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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = [
            "0039-add-oidc-structures-e5d2a8.py",
        ]

    @property
    def migration_id(self):
        return "2f3c1a0e-6dbe-4f55-8c5f-2d7b56c2f2c1"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            """
            CREATE TABLE IF NOT EXISTS secret_rsa_keys (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK
                    (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')),
                "constructor" JSONB NOT NULL,
                "private_key" TEXT NOT NULL,
                "public_key" TEXT NOT NULL,
                "bitness" INTEGER NOT NULL DEFAULT 2048 CHECK
                    (bitness IN (2048, 3072, 4096)),
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS secret_rsa_keys_project_id_idx
                ON secret_rsa_keys (project_id);
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        tables = [
            "secret_rsa_keys",
        ]

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
