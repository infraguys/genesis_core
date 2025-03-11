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

from genesis_core.node import constants as nc


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0007-add-default-roles-73f4c4.py"]

    @property
    def migration_id(self):
        return "0d8f66c9-ecb7-4821-92af-2d7adc931616"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            # TABLES
            """
            CREATE TABLE IF NOT EXISTS n_builders (
                uuid UUID NOT NULL PRIMARY KEY,
                status VARCHAR(32) NOT NULL CHECK (status IN ('ACTIVE', 'DISABLED')),
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS n_machine_pool_reservations (
                uuid UUID NOT NULL PRIMARY KEY,
                cores integer NOT NULL,
                ram integer NOT NULL,
                pool UUID references machine_pools(uuid) ON DELETE CASCADE,
                machine UUID references machines(uuid) ON DELETE CASCADE,
                created_at timestamp NOT NULL DEFAULT current_timestamp,
                updated_at timestamp NOT NULL DEFAULT current_timestamp
            );
            """,
            """
            ALTER TABLE machines 
                ADD IF NOT EXISTS builder UUID references n_builders(uuid) ON DELETE SET NULL;
            """,
            """
            ALTER TABLE machines 
                ADD IF NOT EXISTS build_status VARCHAR(32) NOT NULL CHECK (build_status IN ('IN_BUILD', 'READY')) DEFAULT 'READY';
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS avail_cores integer NOT NULL DEFAULT 0;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS avail_ram integer NOT NULL DEFAULT 0;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS all_cores integer NOT NULL DEFAULT 0;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS all_ram integer NOT NULL DEFAULT 0;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS builder;
            """,
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS build_status;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS avail_cores;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS avail_ram;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS all_cores;
            """,
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS all_ram;
            """,
        ]
        tables = [
            "n_builders",
            "n_machine_pool_reservations",
        ]
        views = []

        for expr in sql_expressions:
            session.execute(expr, None)

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
