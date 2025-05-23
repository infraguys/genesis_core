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
        return "4b802612-3c27-4174-8133-be26a0a05fdb"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS compute_core_agents (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                node UUID references nodes(uuid) ON DELETE SET NULL,
                machine UUID references machines(uuid) ON DELETE CASCADE NULL DEFAULT NULL,
                payload_updated_at timestamp NOT NULL
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_core_agents_node_id_idx
                ON compute_core_agents (node);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_core_agents_machine_id_idx
                ON compute_core_agents (machine);
            """,
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
                ON compute_ports (mac, machine);
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

        tables = [
            "compute_net_interfaces",
            "compute_core_agents",
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


migration_step = MigrationStep()
