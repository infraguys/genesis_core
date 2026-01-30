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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = [
            "0044-add-lb-ext-source-ca08ef.py",
        ]

    @property
    def migration_id(self):
        return "7c2f6d9d-9a28-4d2b-93d6-0e4f7c2a0a56"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                CREATE TABLE IF NOT EXISTS "security_rules" (
                    "uuid" UUID PRIMARY KEY,
                    "name" VARCHAR(255) NOT NULL,
                    "description" VARCHAR(255) NOT NULL DEFAULT '',
                    "project_id" UUID NULL,
                    "condition" JSONB NOT NULL,
                    "verifier" JSONB NOT NULL,
                    "operator" VARCHAR(8) NOT NULL DEFAULT 'OR'
                        CHECK ("operator" IN ('OR', 'AND')),
                    "status" VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                        CHECK ("status" IN ('ACTIVE')),
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
            """
                CREATE INDEX IF NOT EXISTS "security_rules_name_idx" ON
                    "security_rules" ("name");
            """,
            """
                CREATE INDEX IF NOT EXISTS "security_rules_project_id_idx" ON
                    "security_rules" ("project_id");
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables = [
            "security_rules",
        ]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
