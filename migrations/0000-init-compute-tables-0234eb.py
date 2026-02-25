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
        self._depends = [
            "0000-root-d34de1.py",
        ]

    @property
    def migration_id(self):
        return "0234eb6a-82b1-49b8-b266-2d0a7b4deac9"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS machine_agents (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                status VARCHAR(32) NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS machine_pools (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                driver_spec varchar(512) NOT NULL,
                agent UUID references machine_agents(uuid) ON DELETE SET NULL,
                machine_type VARCHAR(2) NOT NULL CHECK (machine_type IN ('VM', 'HW')),
                status VARCHAR(32) NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED', 'MAINTENANCE'))
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS nodes (
                uuid UUID NOT NULL PRIMARY KEY,
                project_id UUID NOT NULL,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                cores integer NOT NULL,
                ram integer NOT NULL,
                image varchar(255) NOT NULL,
                node_type VARCHAR(2) NOT NULL CHECK (node_type IN ('VM', 'HW')),
                status VARCHAR(32) NOT NULL CHECK (status IN ('NEW', 'SCHEDULED', 'IN_PROGRESS', 'STARTED', 'ACTIVE', 'ERROR')),
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS machines (
                uuid UUID NOT NULL PRIMARY KEY,
                project_id UUID NOT NULL,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                cores integer NOT NULL,
                ram integer NOT NULL,
                node UUID references nodes(uuid) ON DELETE CASCADE,
                machine_type VARCHAR(2) NOT NULL CHECK (machine_type IN ('VM', 'HW')),
                boot VARCHAR(8) NOT NULL CHECK (boot IN ('hd0', 'hd1', 'hd2', 'hd3', 'cdrom', 'network')),
                pool UUID references machine_pools(uuid) ON DELETE SET NULL,
                firmware_uuid UUID NULL DEFAULT NULL,
                status VARCHAR(32) NOT NULL CHECK (status IN ('NEW', 'SCHEDULED', 'IN_PROGRESS', 'STARTED', 'ACTIVE', 'IDLE', 'ERROR')),
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
                    nodes.updated_at
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
            """,
            """
            CREATE OR REPLACE VIEW netboots AS
                SELECT
                    machines.firmware_uuid as uuid,
                    machines.boot as boot
                FROM machines;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        tables = [
            "machines",
            "nodes",
            "machine_pools",
            "machine_agents",
        ]
        views = [
            "unscheduled_nodes",
            "netboots",
        ]

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
