#    Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
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
        return "4bd86653-6413-4c4d-9a44-7df58b0acb90"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            DROP VIEW IF EXISTS compute_nodes_without_ports;
            """,
            """
            DROP VIEW IF EXISTS machine_volumes;
            """,
            """
            -- Add disk_spec column to nodes table
            ALTER TABLE nodes 
                ADD COLUMN IF NOT EXISTS disk_spec JSONB;

            -- Fill disk_spec for existing records
            UPDATE nodes 
            SET disk_spec = jsonb_build_object(
                'kind', 'root_disk',
                'size', root_disk_size,
                'image', image
            );

            -- Drop old columns
            ALTER TABLE nodes DROP COLUMN root_disk_size;
            ALTER TABLE nodes DROP COLUMN image;
            """,
            """
            ALTER TABLE nodes 
                ADD IF NOT EXISTS hostname VARCHAR(256) NULL DEFAULT NULL;
            """,
            """
            ALTER TABLE compute_sets
                ADD COLUMN IF NOT EXISTS disk_spec JSONB;

            -- Fill disk_spec for existing records
            UPDATE compute_sets 
            SET disk_spec = jsonb_build_object(
                'kind', 'root_disk',
                'size', root_disk_size,
                'image', image
            );

            -- Drop old columns
            ALTER TABLE compute_sets DROP COLUMN root_disk_size;
            ALTER TABLE compute_sets DROP COLUMN image;
            """,
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS builder;
            """,
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS build_status;
            """,
            """
            ALTER TABLE machines 
                ALTER COLUMN image DROP NOT NULL,
                ALTER COLUMN image SET DEFAULT NULL;
            """,
            """
            ALTER TABLE machines 
                ADD COLUMN IF NOT EXISTS block_devices JSONB DEFAULT '{}';
            """,
            """
            ALTER TABLE node_volumes 
                ADD IF NOT EXISTS status VARCHAR(32) NOT NULL
                CHECK (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')) DEFAULT 'NEW';
            """,
            """
            ALTER TABLE node_volumes 
                ALTER COLUMN device_type TYPE VARCHAR(64);
            """,
            """
            ALTER TABLE node_volumes 
                ADD IF NOT EXISTS index INTEGER DEFAULT 4096;
            """,
            """
            ALTER TABLE node_volumes 
                ADD IF NOT EXISTS pool UUID references machine_pools(uuid) ON DELETE SET NULL;
            """,
            """
            ALTER TABLE node_volumes DROP CONSTRAINT node_volumes_device_type_check;
            """,
            """
            ALTER TABLE node_volumes 
                ADD IF NOT EXISTS image VARCHAR(256) NULL DEFAULT NULL;

            -- Fill image from disk_spec
            UPDATE node_volumes nv
            SET image = (
                SELECT n.disk_spec->>'image'
                    FROM nodes n
                WHERE n.uuid = nv.node
                    AND n.disk_spec IS NOT NULL
                    AND jsonb_typeof(n.disk_spec) = 'object'
                    AND n.disk_spec ? 'image'
            )
            WHERE node IS NOT NULL;

            UPDATE node_volumes SET index=0;
            UPDATE node_volumes SET device_type='';

            -- Put volumes to hidden project if they belong to EM project
            -- Only for migration from legacy schema
            UPDATE node_volumes SET project_id='12345670-6f3a-402e-acf8-0319d53eab58'::uuid  
                WHERE project_id='12345678-c625-4fee-81d5-f691897b8142'::uuid;
            """,
            """
            CREATE TABLE IF NOT EXISTS compute_machine_volumes (
                uuid UUID NOT NULL PRIMARY KEY,
                project_id UUID NOT NULL,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                node_volume UUID references node_volumes(uuid) ON DELETE CASCADE,
                pool UUID references machine_pools(uuid) ON DELETE SET NULL,
                machine UUID references machines(uuid) ON DELETE SET NULL,
                size integer NOT NULL,
                boot bool NOT NULL DEFAULT true,
                index INTEGER NOT NULL DEFAULT 4096,
                label varchar(256) NULL,
                image VARCHAR(256) NULL DEFAULT NULL,
                device_type VARCHAR(64) NOT NULL DEFAULT '',
                status VARCHAR(32) NOT NULL
                    CHECK (status IN (
                        'NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')
                    ) DEFAULT 'NEW',
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            -- Insert data from node_volumes to compute_machine_volumes
            INSERT INTO compute_machine_volumes (
                uuid,
                project_id,
                name,
                description,
                node_volume,
                pool,
                machine,
                size,
                boot,
                index,
                label,
                image,
                device_type,
                status,
                created_at,
                updated_at
            )
            SELECT
                nv.uuid,
                nv.project_id,
                nv.uuid::varchar(255) as name,
                nv.description,
                nv.uuid as node_volume,
                m.pool as pool,
                m.uuid as machine,
                nv.size,
                nv.boot,
                nv.index,
                nv.label,
                nv.image,
                nv.device_type,
                nv.status,
                nv.created_at,
                nv.updated_at
            FROM node_volumes nv
            LEFT JOIN machines m ON m.node = nv.node;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_compute_machine_volumes_project_id
                ON compute_machine_volumes (project_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_compute_machine_volumes_node_volume
                ON compute_machine_volumes (node_volume);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_compute_machine_volumes_pool
                ON compute_machine_volumes (pool);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_compute_machine_volumes_machine
                ON compute_machine_volumes (machine);
            """,
            # Explicitly drop `agent` column to avoid any migration problem
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS agent;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS storage_pools JSONB[] DEFAULT '{}';
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS builder UUID DEFAULT NULL;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS agent UUID DEFAULT NULL;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS cores_ratio FLOAT NOT NULL DEFAULT 1.0;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS ram_ratio FLOAT NOT NULL DEFAULT 1.0;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS created_at timestamp NOT NULL DEFAULT current_timestamp;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS updated_at timestamp NOT NULL DEFAULT current_timestamp;
            """,
            """
            ALTER TABLE machine_pools
                DROP CONSTRAINT IF EXISTS machine_pools_status_check;
            """,
            """
            ALTER TABLE machine_pools 
                ADD CONSTRAINT machine_pools_status_check 
                CHECK (status IN ('ACTIVE', 'DISABLED', 'MAINTENANCE', 'IN_PROGRESS'));
            """,
            """
            DROP TABLE IF EXISTS machine_agents;
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
                    nodes.node_type,
                    nodes.status,
                    nodes.created_at,
                    nodes.updated_at,
                    nodes.default_network,
                    nodes.node_set,
                    nodes.placement_policies,
                    nodes.disk_spec,
                    nodes.hostname
                FROM nodes LEFT JOIN compute_ports as ports ON 
                    nodes.uuid = ports.node WHERE ports.uuid is NULL;
            """,
            """
            CREATE OR REPLACE VIEW compute_unscheduled_volumes AS
                SELECT
                    node_volumes.uuid as uuid,
                    node_volumes.uuid as volume
                FROM node_volumes LEFT JOIN compute_machine_volumes ON 
                    node_volumes.uuid = compute_machine_volumes.node_volume
                    WHERE compute_machine_volumes.uuid is NULL;
            """,
            # Explicitly update the `updated_at` column to initialize
            # updating UA target resource format.
            """
            UPDATE compute_sets
                SET updated_at = current_timestamp;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = [
            """
            DROP VIEW IF EXISTS compute_unscheduled_volumes;
            """,
            """
            DROP VIEW IF EXISTS compute_nodes_without_ports;
            """,
            """
            DROP TABLE IF EXISTS compute_machine_volumes;
            """,
            """
            CREATE TABLE IF NOT EXISTS machine_agents (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                status VARCHAR(32) NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED'))
            );
            """,
            """
            ALTER TABLE machine_pools
                DROP CONSTRAINT IF EXISTS machine_pools_status_check;
            """,
            """
            ALTER TABLE machine_pools 
                ADD CONSTRAINT machine_pools_status_check 
                CHECK (status IN ('ACTIVE', 'DISABLED', 'MAINTENANCE'));
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS created_at;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS updated_at;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS builder;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS storage_pools;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS cores_ratio;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS ram_ratio;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS agent UUID references machine_agents(uuid) ON DELETE SET NULL;
            """,
            """
            ALTER TABLE node_volumes 
                ALTER COLUMN device_type TYPE VARCHAR(16);
            ALTER TABLE node_volumes 
                ALTER COLUMN device_type SET NOT NULL;
            """,
            """
            ALTER TABLE node_volumes 
                DROP COLUMN IF EXISTS status;
            """,
            """
            ALTER TABLE node_volumes 
                DROP COLUMN IF EXISTS image;
            """,
            """
            ALTER TABLE node_volumes 
                DROP COLUMN IF EXISTS pool;
            """,
            """
            ALTER TABLE node_volumes 
                DROP COLUMN IF EXISTS index;
            """,
            """
            ALTER TABLE machines 
                ADD IF NOT EXISTS builder UUID references n_builders(uuid)
                ON DELETE SET NULL;
            """,
            """
            ALTER TABLE machines 
                ADD IF NOT EXISTS build_status VARCHAR(32) NOT NULL
                CHECK (build_status IN ('IN_BUILD', 'READY')) DEFAULT 'READY';
            """,
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS block_devices;
            """,
            """
            ALTER TABLE nodes ADD COLUMN IF NOT EXISTS root_disk_size integer;
            ALTER TABLE nodes ADD COLUMN IF NOT EXISTS image varchar(255);

            UPDATE nodes 
            SET 
                root_disk_size = (disk_spec->>'size')::integer,
                image = disk_spec->>'image'
            WHERE disk_spec IS NOT NULL 
            AND disk_spec->>'kind' = 'root_disk';

            UPDATE nodes 
            SET 
                root_disk_size = COALESCE(root_disk_size, 0),
                image = COALESCE(image, '')
            WHERE root_disk_size IS NULL OR image IS NULL;

            ALTER TABLE nodes ALTER COLUMN image SET NOT NULL;

            ALTER TABLE nodes DROP COLUMN disk_spec;
            """,
            """
            ALTER TABLE nodes
                DROP COLUMN IF EXISTS hostname;
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

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
