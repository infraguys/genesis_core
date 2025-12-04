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
        self._depends = [
            "0034-add-export-adn-import-resources-a12854.py",
            "0035-dummy-placement-e6d5dc.py",
        ]

    @property
    def migration_id(self):
        return "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE
                    iam_clients
                ADD COLUMN IF NOT EXISTS
                    rules JSONB NULL DEFAULT NULL;
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

