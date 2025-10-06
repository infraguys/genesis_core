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
        self._depends = ["0033-em-ua-status-check-5be89c.py"]

    @property
    def migration_id(self):
        return "4bd86653-6413-4c4d-9a44-7df58b0acb90"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS builder;
            """,
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS build_status;
            """,
            """
            ALTER TABLE node_volumes 
                ADD IF NOT EXISTS status VARCHAR(32) NOT NULL
                CHECK (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')) DEFAULT 'NEW';
            """,
            """
            ALTER TABLE machine_volumes 
                ADD IF NOT EXISTS status VARCHAR(32) NOT NULL
                CHECK (status IN ('NEW', 'IN_PROGRESS', 'ACTIVE', 'ERROR')) DEFAULT 'NEW';
            """,
            """
            ALTER TABLE machine_volumes 
                ADD IF NOT EXISTS index INTEGER NOT NULL;
            """,
            # Explicitly drop `agent` column to avoid any migration problem
            """
            ALTER TABLE machine_pools 
                DROP COLUMN IF EXISTS agent;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS builder UUID DEFAULT NULL;
            """,
            """
            DROP TABLE IF EXISTS machine_agents;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = [
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
                DROP COLUMN IF EXISTS builder;
            """,
            """
            ALTER TABLE machine_pools 
                ADD IF NOT EXISTS agent UUID references machine_agents(uuid) ON DELETE SET NULL;
            """,
            """
            ALTER TABLE machine_volumes 
                DROP COLUMN IF EXISTS index;
            """,
            """
            ALTER TABLE machine_volumes 
                DROP COLUMN IF EXISTS status;
            """,
            """
            ALTER TABLE node_volumes 
                DROP COLUMN IF EXISTS status;
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
        ]

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
