# Copyright 2026 Genesis Corporation
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
            "0049-lb-add-proxy-protocol-from-ef8f58.py",
        ]

    @property
    def migration_id(self):
        return "bc80b5db-ee1e-490c-8b17-6b80fc096475"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_users"
                    ADD COLUMN IF NOT EXISTS "custom_props" JSONB NULL DEFAULT NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_users"
                    DROP COLUMN IF EXISTS "custom_props";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
