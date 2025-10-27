# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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
        self._depends = ["0034-add-export-adn-import-resources-a12854.py"]

    @property
    def migration_id(self):
        return "e6d5dcbb-ba98-4f86-8f06-6292eb5ac1a1"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            CREATE TABLE IF NOT EXISTS compute_placement_domains (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_placement_zones (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                domain UUID references compute_placement_domains(uuid) ON DELETE RESTRICT,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_zones_domain_idx
                ON compute_placement_zones (domain);
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_placement_policies (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                project_id UUID NOT NULL,
                domain UUID references compute_placement_domains(uuid) ON DELETE RESTRICT,
                zone UUID references compute_placement_zones(uuid) ON DELETE RESTRICT,
                kind VARCHAR(64) NOT NULL,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_policies_project_id_idx
                ON compute_placement_policies (project_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_policies_domain_idx
                ON compute_placement_policies (domain);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_policies_zone_idx
                ON compute_placement_policies (zone);
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_placement_policy_allocations (
                uuid UUID NOT NULL PRIMARY KEY,
                node UUID references nodes(uuid) ON DELETE CASCADE,
                policy UUID references compute_placement_policies(uuid) ON DELETE CASCADE,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_policy_allocations_node_idx
                ON compute_placement_policy_allocations (node);
            """,
            """
            CREATE INDEX IF NOT EXISTS compute_placement_policy_allocations_policy_idx
                ON compute_placement_policy_allocations (policy);
            """,
            """
            ALTER TABLE nodes
                ADD COLUMN IF NOT EXISTS placement_policies UUID[] NOT NULL;
            """,
            # View
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
                    nodes.default_network,
                    nodes.node_set,
                    nodes.placement_policies
                FROM nodes LEFT JOIN compute_ports as ports ON 
                    nodes.uuid = ports.node WHERE ports.uuid is NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):
        expressions = [
            """
            ALTER TABLE nodes
                DROP COLUMN IF EXISTS placement_policies;
            """,
            """
            DROP TABLE IF EXISTS compute_placement_policy_allocations;
            """,
            """
            DROP TABLE IF EXISTS compute_placement_policies;
            """,
            """
            DROP TABLE IF EXISTS compute_placement_zones;
            """,
            """
            DROP TABLE IF EXISTS compute_placement_domains;
            """,
            # View
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
                    nodes.default_network,
                    nodes.node_set
                FROM nodes LEFT JOIN compute_ports as ports ON 
                    nodes.uuid = ports.node WHERE ports.uuid is NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
