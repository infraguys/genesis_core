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

from genesis_core.compute import constants as nc


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0001-init-all-tables-f47bad.py"]

    @property
    def migration_id(self):
        return "a6972cd6-1cca-43a5-b8f7-47ead0af3eb9"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            f"""
            ALTER TABLE nodes 
                ADD IF NOT EXISTS root_disk_size INTEGER NULL DEFAULT {nc.DEF_ROOT_DISK_SIZE};
            """,
            """
            CREATE TABLE IF NOT EXISTS node_volumes (
                uuid UUID NOT NULL PRIMARY KEY,
                project_id UUID NOT NULL,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                node UUID references nodes(uuid) ON DELETE CASCADE,
                size integer NOT NULL,
                boot bool NOT NULL DEFAULT true,
                label varchar(127) NULL,
                device_type VARCHAR(16) NOT NULL CHECK (device_type IN ('QCOW2')),
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            # VIEWS
            """
            CREATE OR REPLACE VIEW unscheduled_nodes AS
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
                    nodes.root_disk_size
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
            """,
            """
            CREATE OR REPLACE VIEW machine_volumes AS
                SELECT
                    node_volumes.uuid,
                    node_volumes.project_id,
                    node_volumes.name,
                    node_volumes.description,
                    node_volumes.node,
                    node_volumes.size,
                    node_volumes.boot,
                    node_volumes.label,
                    node_volumes.device_type,
                    machines.uuid as machine,
                    node_volumes.created_at,
                    node_volumes.updated_at
                FROM node_volumes LEFT JOIN machines ON 
                    node_volumes.node = machines.node;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        tables = [
            "node_volumes",
        ]
        views = [
            "machine_volumes",
        ]

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
