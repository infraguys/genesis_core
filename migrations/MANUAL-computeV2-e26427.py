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
        self._depends = ["0042-compute-ua-integration-4bd866.py"]

    @property
    def migration_id(self):
        return "e26427e5-b510-49d1-a178-22ada1e8ce51"

    @property
    def is_manual(self):
        return True

    def upgrade(self, session):
        expressions = [
            """
            -- Temporary delete machine pools of type HW. They are not used.
            DELETE FROM machine_pools
                WHERE machine_type = 'HW';
            """,
            """
            -- Put volumes to hidden project if they belong to EM project
            -- Only for migration from legacy schema
            UPDATE node_volumes SET project_id='12345670-6f3a-402e-acf8-0319d53eab58'::uuid  
                WHERE project_id='12345678-c625-4fee-81d5-f691897b8142'::uuid;
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
            # Explicitly update the `updated_at` column to initialize
            # updating UA target resource format.
            """
            UPDATE compute_sets
                SET updated_at = current_timestamp;
            """,
            # Manual migration
            """
            -- [node_set] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT res_uuid, value, kind FROM ua_target_resources WHERE kind='node_set'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.value->>'uuid',
                        'cores', rec.value->'cores',
                        'replicas', rec.value->'replicas',
                        'set_type', rec.value->>'set_type',
                        'node_type', rec.value->>'node_type',
                        'project_id', rec.value->>'project_id',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE ua_target_resources 
                    SET value = new_value 
                    WHERE res_uuid = rec.res_uuid;
                END LOOP;
            END $$;
            """,
            """
            -- [em_core_compute_sets] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT res_uuid, value, kind FROM ua_target_resources WHERE kind='em_core_compute_sets'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.value->>'uuid',
                        'cores', rec.value->'cores',
                        'replicas', rec.value->'replicas',
                        'project_id', rec.value->>'project_id',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE ua_target_resources 
                    SET value = new_value 
                    WHERE res_uuid = rec.res_uuid;
                END LOOP;
            END $$;
            """,
            """
            -- [set_agent_node] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT res_uuid, value, kind FROM ua_target_resources WHERE kind='set_agent_node'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.value->>'uuid',
                        'cores', rec.value->'cores',
                        'node_type', rec.value->>'node_type',
                        'project_id', rec.value->>'project_id',
                        'placement_policies', rec.value->'placement_policies',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE ua_target_resources 
                    SET value = new_value 
                    WHERE res_uuid = rec.res_uuid;
                END LOOP;
            END $$;
            """,
            """
            -- [em_core_compute_nodes] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT res_uuid, value, kind FROM ua_target_resources WHERE kind='em_core_compute_nodes'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.value->>'uuid',
                        'cores', rec.value->'cores',
                        'project_id', rec.value->>'project_id',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE ua_target_resources 
                    SET value = new_value 
                    WHERE res_uuid = rec.res_uuid;
                END LOOP;
            END $$;
            """,
            """
            DELETE FROM ua_actual_resources WHERE 
                kind='em_core_compute_nodes' OR
                kind='em_core_compute_sets' OR
                kind='set_agent_node' OR
                kind='node_set' OR
                kind='target_node_set';
            """,
            """
            UPDATE nodes 
                SET hostname = REPLACE(name, '_', '-')
                WHERE hostname IS NULL OR hostname = '';
            """,
            """
            -- [$core.compute.nodes] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT uuid, value, resource_link_prefix FROM em_resources WHERE resource_link_prefix='$core.compute.nodes'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.uuid,
                        'cores', rec.value->'cores',
                        'project_id', rec.value->>'project_id',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE em_resources 
                    SET value = new_value 
                    WHERE uuid = rec.uuid;
                END LOOP;
            END $$;
            """,
            """
            -- [$core.compute.sets] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT uuid, value, resource_link_prefix FROM em_resources WHERE resource_link_prefix='$core.compute.sets'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.uuid,
                        'cores', rec.value->'cores',
                        'project_id', rec.value->>'project_id',
                        'replicas', rec.value->'replicas',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE em_resources 
                    SET value = new_value 
                    WHERE uuid = rec.uuid;
                END LOOP;
            END $$;
            """,
            """
            -- [target_node_set] Migration for adding disk_spec structure to JSONB field value
            DO $$
            DECLARE
                rec RECORD;
                new_value JSONB;
            BEGIN
                FOR rec IN SELECT res_uuid, value, kind FROM ua_target_resources WHERE kind='target_node_set'
                LOOP
                    -- Create new JSONB value
                    new_value := jsonb_build_object(
                        'ram', rec.value->'ram',
                        'name', rec.value->>'name',
                        'uuid', rec.value->>'uuid',
                        'cores', rec.value->'cores',
                        'replicas', rec.value->'replicas',
                        'node_type', rec.value->>'node_type',
                        'set_type', rec.value->>'set_type',
                        'project_id', rec.value->>'project_id',
                        'disk_spec', jsonb_build_object(
                            'kind', 'root_disk',
                            'size', rec.value->'root_disk_size',
                            'image', rec.value->>'image'
                        )
                    );
                    
                    -- Update record
                    UPDATE ua_target_resources 
                    SET value = new_value 
                    WHERE res_uuid = rec.res_uuid;
                END LOOP;
            END $$;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = []

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
