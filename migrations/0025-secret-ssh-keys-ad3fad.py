# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        # self._depends = ["MANUAL-fix-usernames-6b042b.py"]
        self._depends = ["0024-user_confirmation_code_made_at-added-435e66.py"]

    @property
    def migration_id(self):
        return "ad3fadc1-b50c-4378-a570-86db321616d6"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS secret_ssh_keys (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK 
                    (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')),
                "constructor" JSONB NOT NULL,
                "target" JSONB NOT NULL,
                "user" varchar(64) NOT NULL,
                "authorized_keys" varchar(256) NOT NULL,
                "target_public_key" TEXT NULL DEFAULT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp,
                UNIQUE ("user", "target", "target_public_key")
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS secret_ssh_keys_project_id_idx
                ON secret_ssh_keys (project_id);
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        tables = [
            "secret_ssh_keys",
        ]

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
