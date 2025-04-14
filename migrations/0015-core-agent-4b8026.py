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
        self._depends = ["0014-network-ipam-067981.py"]

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
            CREATE TABLE IF NOT EXISTS computes_core_agents (
                uuid UUID NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                description varchar(255) NOT NULL,
                node UUID references nodes(uuid) ON DELETE SET NULL,
                payload_updated_at timestamp NOT NULL
            );
            """,
            """
            CREATE INDEX IF NOT EXISTS computes_core_agents_node_id_idx
                ON computes_core_agents (node);
            """,
            """
            ALTER TABLE compute_subnets 
                ADD IF NOT EXISTS ip_discovery_range varchar(31) NULL DEFAULT NULL;
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
        ]
        tables = [
            "computes_core_agents",
        ]
        views = []

        for view_name in views:
            self._delete_view_if_exists(session, view_name)

        for expr in sql_expressions:
            session.execute(expr, None)

        for table_name in tables:
            self._delete_table_if_exists(session, table_name)


migration_step = MigrationStep()
