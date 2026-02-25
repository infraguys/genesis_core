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


class MigrationStep(migrations.AbstractMigrationStep):
    def __init__(self):
        self._depends = [
            "0043-add-user-source-4f5e1f.py",
        ]

    @property
    def migration_id(self):
        return "ca08ef4a-f781-4b85-82ce-9a69602f1434"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "net_lb_vhosts"
                ADD COLUMN IF NOT EXISTS "external_sources" JSONB[] NOT NULL DEFAULT '{}';
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "net_lb_vhosts"
                DROP COLUMN IF EXISTS "external_sources";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
