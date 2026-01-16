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
        self._depends = []

    @property
    def migration_id(self):
        return "12db0312-4ac4-4591-b80a-b2db5a593842"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE
                    iam_clients
                ADD COLUMN IF NOT EXISTS
                    rules JSONB NULL DEFAULT '[]'::jsonb;
            """,
            """
                UPDATE iam_clients
                SET rules = '[]'::jsonb
                WHERE rules IS NULL;
            """,
        ]

        for expr in expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE
                    iam_clients
                DROP COLUMN IF EXISTS
                    rules;
            """,
        ]

        for expr in expressions:
            session.execute(expr, None)


migration_step = MigrationStep()
