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
        self._depends = ["0021-dns-permissions-7adac7.py"]

    @property
    def migration_id(self):
        return "d340e85d-c244-43c9-8844-f509179a69fb"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS secret_certificates (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK 
                    (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')),
                "constructor" JSONB NOT NULL,
                "method" JSONB NOT NULL,
                "email" varchar(254) NOT NULL,
                "domains" varchar(1024) NOT NULL,
                "key" TEXT NULL DEFAULT NULL,
                "cert" TEXT NULL DEFAULT NULL,
                "expiration_at" timestamp NULL DEFAULT NULL,
                "expiration_threshold" integer NOT NULL,
                "overcome_threshold" boolean DEFAULT false,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS secret_certificates_project_id_idx
                ON secret_certificates (project_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS storage_certs (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "status" VARCHAR(32) NOT NULL CHECK 
                    (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')),
                "pkey" varchar(10240) NOT NULL,
                "fullchain" varchar(10240) NOT NULL,
                "csr" varchar(10240) NOT NULL,
                "expiration_at" timestamp NOT NULL,
                "meta" JSONB NOT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        tables = [
            "storage_certs",
            "secret_certificates",
        ]

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
