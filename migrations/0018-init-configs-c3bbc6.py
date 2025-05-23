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
        self._depends = ["0017-core-agent-4b8026.py"]

    @property
    def migration_id(self):
        return "c3bbc6b2-bc9a-4436-9496-515b3b701220"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TYPE "enum_config_status" AS ENUM (
                'NEW',
                'IN_PROGRESS',
                'ACTIVE',
                'ERROR'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS config_configs (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "project_id" UUID NOT NULL,
                "status" enum_config_status NOT NULL DEFAULT 'NEW',
                "path" varchar(255) NOT NULL,
                "target" JSONB NOT NULL,
                "body" JSONB NOT NULL,
                "on_change" JSONB NOT NULL,
                "mode" char(4) NOT NULL,
                "owner" varchar(128) NOT NULL,
                "group" varchar(128) NOT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS config_configs_project_id_idx
                ON config_configs (project_id);
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS config_configs_path_target_id_idx
                ON config_configs (path, target);
            """,
            """
            CREATE INDEX IF NOT EXISTS config_configs_new_in_progress_id_idx
                ON config_configs (status)
                WHERE status = 'NEW' or status = 'IN_PROGRESS';
            """,
            """
            CREATE TABLE IF NOT EXISTS config_renders (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "status" enum_config_status NOT NULL DEFAULT 'NEW',
                "content" text NOT NULL,
                "config" UUID references config_configs(uuid) ON DELETE CASCADE,
                "node" UUID references nodes(uuid) ON DELETE CASCADE,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS config_renders_config_id_idx
                ON config_renders (config);
            """,
            """
            CREATE INDEX IF NOT EXISTS config_renders_node_id_idx
                ON config_renders (node);
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_types = [
            """
            DROP TYPE IF EXISTS enum_config_status;
            """,
        ]

        tables = [
            "config_renders",
            "config_configs",
        ]

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)

        for expr in sql_types:
            session.execute(expr, None)


migration_step = MigrationStep()
