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
        self._depends = ["0019-init-dns-40a307.py"]

    @property
    def migration_id(self):
        return "a643b104-f95d-47cd-aaa8-55a1a0104ba6"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            DROP TYPE IF EXISTS enum_secret_status;
            CREATE TYPE "enum_secret_status" AS ENUM (
                'NEW',
                'IN_PROGRESS',
                'ACTIVE',
                'ERROR'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS secret_passwords (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" enum_secret_status NOT NULL DEFAULT 'NEW',
                "constructor" JSONB NOT NULL,
                "value" varchar(512) NULL DEFAULT NULL,
                "method" varchar(64) NOT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS secret_passwords_project_id_idx
                ON secret_passwords (project_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS storage_passwords (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "status" enum_secret_status NOT NULL DEFAULT 'NEW',
                "value" varchar(512) NOT NULL,
                "meta" JSONB NOT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_types = [
            """
            DROP TYPE IF EXISTS enum_secret_status;
            """,
        ]

        tables = [
            "storage_passwords",
            "secret_passwords",
        ]

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)

        for expr in sql_types:
            session.execute(expr, None)


migration_step = MigrationStep()
