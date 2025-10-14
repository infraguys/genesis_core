# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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
        self._depends = ["0033-em-ua-status-check-5be89c.py"]

    @property
    def migration_id(self):
        return "a12854ea-14af-4d9c-b8a8-a7925263eacf"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE
                    em_manifests
                ADD COLUMN IF NOT EXISTS
                    exports JSONB NOT NULL DEFAULT '{}';
            """,
            """
                ALTER TABLE
                    em_manifests
                ADD COLUMN IF NOT EXISTS
                    imports JSONB NOT NULL DEFAULT '{}';
            """,
            """
                CREATE TABLE IF NOT EXISTS "em_exports" (
                    "uuid" UUID PRIMARY KEY,
                    "element" UUID NOT NULL REFERENCES em_elements("uuid")
                        ON DELETE CASCADE,
                    "name" VARCHAR(255) NOT NULL,
                    "kind" VARCHAR(20) NOT NULL DEFAULT 'resource'
                        CHECK (
                            kind IN (
                                'resource'
                            )
                        ),
                    "link" VARCHAR(255) NOT NULL,
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS "em_imports" (
                    "uuid" UUID PRIMARY KEY,
                    "element" UUID NOT NULL REFERENCES em_elements("uuid")
                        ON DELETE CASCADE,
                    "from_element" UUID NOT NULL REFERENCES em_elements("uuid")
                        ON DELETE CASCADE,
                    "from_resource" UUID NOT NULL REFERENCES
                        em_resources("uuid")
                        ON DELETE CASCADE,
                    "name" VARCHAR(255) NOT NULL,
                    "kind" VARCHAR(20) NOT NULL DEFAULT 'resource'
                        CHECK (
                            kind IN (
                                'resource'
                            )
                        ),
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE em_manifests DROP COLUMN IF EXISTS
                    exports;
            """,
            """
                ALTER TABLE em_manifests DROP COLUMN IF EXISTS
                    imports;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

        self._delete_table_if_exists(session, "em_imports")
        self._delete_table_if_exists(session, "em_exports")


migration_step = MigrationStep()
