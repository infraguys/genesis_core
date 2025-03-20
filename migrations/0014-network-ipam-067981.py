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
        self._depends = ["0013-add-ttl-to-token-2b8e3e.py"]

    @property
    def migration_id(self):
        return "067981fb-487e-4ec7-8141-b84569af759b"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS compute_networks (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                project_id UUID NOT NULL,
                driver_spec varchar(512) NOT NULL DEFAULT '{}',
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_networks_project_id_idx
                ON compute_networks (project_id);
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_subnets (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                project_id UUID NOT NULL,
                network UUID references compute_networks(uuid) ON DELETE RESTRICT,
                cidr varchar(18) NOT NULL,
                ip_range varchar(31) NULL DEFAULT NULL,
                dhcp boolean DEFAULT true,
                dns_servers varchar(512) NOT NULL DEFAULT '{}',
                routers varchar(512) NOT NULL DEFAULT '{}',
                next_server varchar(256) NULL DEFAULT '127.0.0.1',
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_subnets_project_id_idx
                ON compute_subnets (project_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_subnets_network_id_idx
                ON compute_subnets (network);
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_ports (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                project_id UUID NOT NULL,
                subnet UUID references compute_subnets(uuid) ON DELETE RESTRICT,
                node UUID references nodes(uuid) ON DELETE CASCADE,
                machine UUID references machines(uuid) ON DELETE CASCADE,
                interface varchar(32) NULL DEFAULT NULL,
                target_ipv4 varchar(15) NULL DEFAULT NULL,
                target_mask varchar(15) NULL DEFAULT NULL,
                ipv4 varchar(15) NULL DEFAULT NULL,
                mask varchar(15) NULL DEFAULT NULL,
                mac varchar(17) NULL DEFAULT NULL,
                status VARCHAR(32) NOT NULL CHECK (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')),
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_ports_project_id_idx
                ON compute_ports (project_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_ports_subnet_id_idx
                ON compute_ports (subnet);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_ports_node_id_idx
                ON compute_ports (node);
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS compute_ports_target_ipv4_subnet_id_idx
                ON compute_ports (target_ipv4, subnet);
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS compute_ports_mac_subnet_id_idx
                ON compute_ports (mac, subnet);
            """,
            """
            ALTER TABLE nodes 
                ADD IF NOT EXISTS default_network varchar(255) NULL DEFAULT NULL;
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
                    nodes.root_disk_size,
                    nodes.default_network
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
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
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
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
                    nodes.root_disk_size
                FROM nodes LEFT JOIN machines ON 
                    nodes.uuid = machines.node WHERE machines.uuid is NULL;
            """,
            """
            ALTER TABLE nodes 
                DROP COLUMN IF EXISTS default_network;
            """,
        ]
        tables = [
            "compute_ports",
            "compute_subnets",
            "compute_networks",
        ]
        views = ["compute_nodes_without_ports"]

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
