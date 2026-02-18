# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
# Copyright 2025 Genesis Corporation
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
        self._depends = ["0045-add-security-rules-7c2f6d.py"]

    @property
    def migration_id(self):
        return "f5aaa29d-2f90-445f-b7d1-74f36b06a6d5"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            """
            CREATE TABLE IF NOT EXISTS vs_profiles (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK (
                    status IN (
                        'NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR'
                    )
                ),
                "profile_type" VARCHAR(32) NOT NULL CHECK (
                    profile_type IN (
                        'GLOBAL', 'ELEMENT'
                    )
                ),
                "active" BOOL DEFAULT 'f',
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp,
                UNIQUE (name)
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS vs_profiles_project_id_idx
                ON vs_profiles (project_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS vs_profiles_profile_type_idx
                ON vs_profiles (profile_type);
            """,
            """
            CREATE TABLE IF NOT EXISTS vs_variables (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK (
                    status IN (
                        'NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR'
                    )
                ),
                "setter" JSONB NOT NULL,
                "value" JSONB NULL DEFAULT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS vs_variables_project_id_idx
                ON vs_variables (project_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS vs_values (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" VARCHAR(32) NOT NULL CHECK (
                    status IN (
                        'NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR'
                    )
                ),
                "value" JSONB NULL DEFAULT NULL,
                "read_only" BOOL DEFAULT 'f',
                "manual_selected" BOOL DEFAULT 'f',
                "variable" UUID NULL DEFAULT NULL REFERENCES vs_variables("uuid") ON DELETE SET NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE UNIQUE INDEX vs_values_one_manual_selected_per_variable 
                ON vs_values (variable) 
                WHERE manual_selected = true;
            """,
            """
            CREATE INDEX IF NOT EXISTS vs_values_project_id_idx
                ON vs_values (project_id);
            """,
            """
            ALTER TABLE em_elements
                ADD COLUMN IF NOT EXISTS profile UUID NULL DEFAULT NULL REFERENCES vs_profiles("uuid") ON DELETE RESTRICT;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE em_elements
                DROP COLUMN IF EXISTS profile;
            """,
        ]

        tables = [
            "vs_values",
            "vs_variables",
            "vs_profiles",
        ]
        views = []

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
