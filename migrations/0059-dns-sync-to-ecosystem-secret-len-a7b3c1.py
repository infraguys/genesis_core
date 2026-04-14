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
            "0058-copy-iam-users-target-to-actual-resources-a1b2c3.py",
        ]

    @property
    def migration_id(self):
        return "a7b3c1d2-5e4f-4a3b-9c8d-7e6f5a4b3c2d"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "dns_domains"
                ADD COLUMN IF NOT EXISTS "sync_to_ecosystem"
                    BOOLEAN NOT NULL DEFAULT FALSE;
            """,
            """
                CREATE INDEX IF NOT EXISTS dns_records_updated_at_idx
                    ON dns_records (updated_at);
            """,
            """
                ALTER TABLE "secret_passwords"
                ADD COLUMN IF NOT EXISTS "default_length"
                    INTEGER NOT NULL DEFAULT 32;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                DROP INDEX IF EXISTS dns_records_updated_at_idx;
            """,
            """
                ALTER TABLE "secret_passwords"
                DROP COLUMN IF EXISTS "default_length";
            """,
            """
                ALTER TABLE "dns_domains"
                DROP COLUMN IF EXISTS "sync_to_ecosystem";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
