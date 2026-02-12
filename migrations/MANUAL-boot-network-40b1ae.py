#    Copyright 2026 Genesis Corporation.
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
        self._depends = ["0051-sdk-1-5-0-migration-eea262.py"]

    @property
    def migration_id(self):
        return "40b1aeb9-bbe0-4bd9-90fe-adecab5b719b"

    @property
    def is_manual(self):
        return True

    def upgrade(self, session):
        expressions = [
            """
            DO $$
            DECLARE
                subnets_count integer;
                first_subnet record;
            BEGIN
                SELECT COUNT(*) INTO subnets_count FROM compute_subnets;

                IF subnets_count < 2 THEN
                    IF subnets_count = 0 THEN
                        RETURN;
                    END IF;

                    SELECT * INTO first_subnet
                    FROM compute_subnets
                    ORDER BY created_at ASC, uuid ASC
                    LIMIT 1;

                    UPDATE compute_subnets
                    SET
                        name = 'br0',
                        next_server = NULL
                    WHERE uuid = first_subnet.uuid;

                    INSERT INTO compute_subnets (
                        uuid,
                        name,
                        description,
                        project_id,
                        network,
                        cidr,
                        ip_range,
                        dhcp,
                        dns_servers,
                        routers,
                        next_server,
                        ip_discovery_range
                    ) VALUES (
                        gen_random_uuid(),
                        'br1',
                        '',
                        '00000000-0000-0000-0000-000000000000'::uuid,
                        first_subnet.network,
                        '10.100.0.0/22',
                        NULL,
                        true,
                        '["10.20.0.0"]',
                        '[{"to":"0.0.0.0/0","via":"10.100.0.2"}]',
                        '10.100.0.2',
                        '10.100.0.10-10.100.0.254'
                    );
                END IF;
            END $$;
            """,
            """
            UPDATE ua_target_resources
            SET value = jsonb_set(
                value,
                '{port_info,source}',
                '"br0"'::jsonb,
                true
            )
            WHERE kind = 'pool_machine'
              AND (value ? 'port_info')
              AND jsonb_typeof(value->'port_info') = 'object'
              AND NOT ((value->'port_info') ? 'source');
            """,
            """
            UPDATE ua_target_resources
            SET value = jsonb_set(
                value,
                '{boot}',
                '"hd0"'::jsonb,
                true
            )
            WHERE kind = 'pool_machine'
              AND (value ? 'boot')
              AND value->>'boot' <> 'hd0';
            """,
            """
            UPDATE ua_target_resources
            SET value = jsonb_set(
                value,
                '{port_info}',
                (value->'port_info') - 'uuid' - 'subnet',
                true
            )
            WHERE kind = 'pool_machine'
              AND (value ? 'port_info')
              AND jsonb_typeof(value->'port_info') = 'object'
              AND (
                    (value->'port_info') ? 'uuid'
                    OR (value->'port_info') ? 'subnet'
              );
            """,
            """
            INSERT INTO ua_node_encryption_keys (
                uuid,
                private_key,
                encryption_disabled_until
            )
            SELECT
                nodes.uuid,
                encode(
                    decode(
                        md5(random()::text || clock_timestamp()::text || nodes.uuid::text)
                        || md5(clock_timestamp()::text || random()::text || nodes.uuid::text),
                        'hex'
                    ),
                    'base64'
                ),
                '2028-12-31 23:59:59'::timestamp
            FROM nodes
            ON CONFLICT (uuid) DO NOTHING;
            """,
            """
            UPDATE compute_ports
                SET source = 'br0';
            """,
            """
            UPDATE machines
                SET updated_at = current_timestamp;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = []

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
