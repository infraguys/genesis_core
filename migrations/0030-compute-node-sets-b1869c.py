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
        self._depends = ["0029-sdk-0-7-0-migration-c2c52a.py"]

    @property
    def migration_id(self):
        return "b1869cc2-82c0-42e8-a6a9-df07105c3df5"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS compute_sets (
                "uuid" UUID NOT NULL PRIMARY KEY,
                "project_id" UUID NOT NULL,
                "name" varchar(255) NOT NULL,
                "description" varchar(255) NOT NULL,
                "cores" integer NOT NULL,
                "ram" integer NOT NULL,
                "root_disk_size" integer NOT NULL,
                "replicas" integer NOT NULL,
                "image" varchar(255) NOT NULL,
                "node_type" VARCHAR(2) NOT NULL CHECK (node_type IN ('VM', 'HW')),
                "set_type" VARCHAR(32) NOT NULL CHECK (set_type IN ('SET')),
                "status" VARCHAR(32) NOT NULL CHECK (status IN ('NEW', 'SCHEDULED', 'IN_PROGRESS', 'STARTED', 'ACTIVE', 'ERROR')),
                "nodes" JSONB NOT NULL,
                "default_network" JSONB NOT NULL,
                "created_at" timestamp NOT NULL DEFAULT current_timestamp,
                "updated_at" timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_sets_project_id_idx
                ON compute_sets (project_id);
            """,
            """
            ALTER TABLE nodes 
                ADD IF NOT EXISTS node_set UUID references compute_sets(uuid) ON DELETE CASCADE;
            """,
            # VIEWS
            """
            CREATE OR REPLACE VIEW compute_nodes_without_ports AS
                SELECT
                    nodes.uuid,
                    nodes.project_id,
                    nodes.name,
                    nodes.description,
                    nodes.cores,
                    nodes.ram,
                    nodes.image,
                    nodes.node_type,
                    nodes.status,
                    nodes.created_at,
                    nodes.updated_at,
                    nodes.root_disk_size,
                    nodes.default_network,
                    nodes.node_set
                FROM nodes LEFT JOIN compute_ports as ports ON 
                    nodes.uuid = ports.node WHERE ports.uuid is NULL;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
            """
            DROP VIEW IF EXISTS compute_nodes_without_ports;
            """,
            """
            CREATE OR REPLACE VIEW compute_nodes_without_ports AS
                SELECT
                    nodes.uuid,
                    nodes.project_id,
                    nodes.name,
                    nodes.description,
                    nodes.cores,
                    nodes.ram,
                    nodes.image,
                    nodes.node_type,
                    nodes.status,
                    nodes.created_at,
                    nodes.updated_at,
                    nodes.root_disk_size,
                    nodes.default_network
                FROM nodes LEFT JOIN compute_ports as ports ON 
                    nodes.uuid = ports.node WHERE ports.uuid is NULL;
            """,
            """
            ALTER TABLE nodes 
                DROP COLUMN IF EXISTS node_set;
            """,
        ]
        tables = [
            "compute_sets",
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
