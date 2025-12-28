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
            "0042-compute-ua-integration-4bd866.py",
        ]

    @property
    def migration_id(self):
        return "4f5e1f94-0f37-4c24-8c37-522ce3c6c5c6"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_users"
                ADD COLUMN IF NOT EXISTS "user_source" JSONB
                    NOT NULL DEFAULT '{"kind": "IAM"}'::jsonb;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_users"
                DROP COLUMN IF EXISTS "user_source";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
