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
            "0040-secret-rsa-keys-2f3c1a.py",
        ]

    @property
    def migration_id(self):
        return "18d7c4a6-9ee0-4b1a-8fa2-9a0a1f9cfbcb"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                DROP INDEX IF EXISTS "iam_idp_id_idx";
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "client_id";
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "secret_hash";
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "salt";
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "client_id" VARCHAR(64)
                    NOT NULL DEFAULT '';
            """,
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "secret_hash" CHAR(128)
                    NOT NULL DEFAULT '';
            """,
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "salt" CHAR(24)
                    NOT NULL DEFAULT '';
            """,
            """
                CREATE UNIQUE INDEX IF NOT EXISTS "iam_idp_id_idx"
                    ON "iam_idp" ("client_id");
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
