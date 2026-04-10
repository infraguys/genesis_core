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
        self._depends = ["0056-iam-user-create-perm-3e0dc5.py"]

    @property
    def migration_id(self):
        return "3bc13835-4fe9-4f04-b394-60a0748d4ea1"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            ALTER TABLE "em_elements"
                ADD COLUMN IF NOT EXISTS "project_id" UUID DEFAULT NULL;
            """,
            """
            ALTER TABLE "em_elements"
                ADD COLUMN IF NOT EXISTS "requirements" JSONB NOT NULL DEFAULT '{}';
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "em_elements" DROP COLUMN IF EXISTS "project_id";
            """,
            """
                ALTER TABLE "em_elements" DROP COLUMN IF EXISTS "requirements";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
