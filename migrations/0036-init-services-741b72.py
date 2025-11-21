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


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0035-dummy-placement-e6d5dc.py"]

    @property
    def migration_id(self):
        return "741b7266-19e8-448b-9463-1c55ec174e28"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            DROP TYPE IF EXISTS enum_service_status;
            CREATE TYPE "enum_service_status" AS ENUM (
                'NEW',
                'IN_PROGRESS',
                'ACTIVE',
                'ERROR'
            );
            """,
            """
            DROP TYPE IF EXISTS enum_service_target_status;
            CREATE TYPE "enum_service_target_status" AS ENUM (
                'enabled',
                'disabled'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS em_services (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" enum_service_status NOT NULL DEFAULT 'NEW',
                "target_status" enum_service_target_status NOT NULL DEFAULT 'enabled',
                "path" varchar(255) NOT NULL,
                "target" JSONB NOT NULL,
                "service_type" JSONB NOT NULL,
                "before" JSONB[],
                "after" JSONB[],
                "user" varchar(255) NOT NULL,
                "group" varchar(255),
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS em_services_project_id_idx
                ON em_services (project_id);
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS em_services_path_target_id_idx
                ON em_services (path, target);
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = []

        sql_types = [
            """
            DROP TYPE IF EXISTS enum_service_status;
            """,
            """
            DROP TYPE IF EXISTS enum_service_target_status;
            """,
        ]

        tables = [
            "em_services",
        ]
        views = []

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)

        for expr in sql_types:
            session.execute(expr, None)


migration_step = MigrationStep()
