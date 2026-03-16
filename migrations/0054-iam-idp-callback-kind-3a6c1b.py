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
            "0053-lb-node-secret-set-permissions-11c9a8.py",
        ]

    @property
    def migration_id(self):
        return "3a6c1b7a-20a0-4d3b-8896-d183f5eb2e6b"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "callback" JSONB
                    NOT NULL DEFAULT '{"kind": "callback_uri", "callback": ""}'::jsonb;
            """,
            """
                UPDATE "iam_idp"
                SET "callback" = jsonb_build_object(
                    'kind', 'callback_uri',
                    'callback', COALESCE("callback_uri", '')
                );
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "callback_uri";
            """,
            """
                DELETE FROM "iam_idp_authorization_info";
            """,
            """
                ALTER TABLE "iam_idp_authorization_info"
                ADD COLUMN IF NOT EXISTS "redirect_uri" VARCHAR(256)
                    NOT NULL DEFAULT '';
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "callback_uri" VARCHAR(256)
                    NOT NULL DEFAULT '';
            """,
            """
                UPDATE "iam_idp"
                SET "callback_uri" = COALESCE("callback"->>'callback', '');
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "callback";
            """,
            """
                ALTER TABLE "iam_idp_authorization_info"
                DROP COLUMN IF EXISTS "redirect_uri";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
