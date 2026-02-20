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
        self._depends = ["0016-add-permissions-to-all-iam-resources-3b82c6.py"]

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
            ALTER TABLE compute_subnets 
                ADD IF NOT EXISTS ip_discovery_range varchar(31) NULL DEFAULT NULL;
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_net_interfaces (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                machine UUID references machines(uuid) ON DELETE CASCADE,
                ipv4 varchar(15) NULL DEFAULT NULL,
                mask varchar(15) NULL DEFAULT NULL,
                mac varchar(17) NULL DEFAULT NULL,
                mtu integer DEFAULT 1500,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_net_interfaces_machine_id_idx
                ON compute_net_interfaces (machine);
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS compute_net_interfaces_mac_machine_id_idx
                ON compute_net_interfaces (mac, machine);
            """,
            """
            DROP TYPE IF EXISTS enum_config_status;
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
            # Views
            """
            DROP VIEW IF EXISTS unscheduled_nodes;
            """,
            """
            CREATE OR REPLACE VIEW unscheduled_nodes AS
                SELECT
                    nodes.uuid as uuid,
                    nodes.uuid as node
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
            """,
            """
            CREATE OR REPLACE VIEW compute_hw_nodes_without_ports AS
                SELECT
                    nodes.uuid as uuid,
                    nodes.uuid as node,
                    machines.uuid as machine,
                    compute_net_interfaces.uuid as iface
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node
                LEFT JOIN compute_net_interfaces ON
                    compute_net_interfaces.machine = machines.uuid
                LEFT JOIN compute_ports ON
                    compute_ports.node = nodes.uuid
                WHERE nodes.node_type = 'HW' AND machines.uuid is not NULL AND compute_net_interfaces.ipv4 is not NULL AND compute_ports.uuid is NULL;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE compute_subnets 
                DROP COLUMN IF EXISTS ip_discovery_range;
            """,
            """
            DROP VIEW IF EXISTS unscheduled_nodes;
            """,
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
                    nodes.root_disk_size,
                    nodes.default_network
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
            """,
        ]

        sql_types = [
            """
            DROP TYPE IF EXISTS enum_config_status;
            """,
        ]

        tables = [
            "config_configs",
            "compute_net_interfaces",
        ]
        views = [
            "compute_hw_nodes_without_ports",
        ]

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)

        for expr in sql_types:
            session.execute(expr, None)


migration_step = MigrationStep()
