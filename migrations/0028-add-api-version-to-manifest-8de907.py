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


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0027-email-lowercase-unique-constraint-98a7bb.py"]

    @property
    def migration_id(self):
        return "8de907a2-768c-4285-aa82-de0eba3d01db"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            ALTER TABLE "em_manifests"
                ADD COLUMN IF NOT EXISTS "api_version" VARCHAR(16)
                DEFAULT NULL;
            """,
            """
            ALTER TABLE "em_elements"
                ADD COLUMN IF NOT EXISTS "api_version" VARCHAR(16)
                DEFAULT NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "em_manifests" DROP COLUMN IF EXISTS "api_version";
            """,
            """
                ALTER TABLE "em_elements" DROP COLUMN IF EXISTS "api_version";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
