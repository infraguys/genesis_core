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

_DEFAULT_IAM_CLIENT_UUID = "00000000-0000-0000-0000-000000000000"


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = [
            "0038-init-lb-e88603.py",
        ]

    @property
    def migration_id(self):
        return "e5d2a8e0-6c4a-4a0e-9f0d-3c4b2a1d9e50"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE iam_idp
                RENAME COLUMN redirect_uri_template TO callback_uri;
            """,
            """
                ALTER TABLE iam_idp
                DROP COLUMN IF EXISTS well_known_endpoint;
            """,
            """
                ALTER TABLE "iam_idp"
                ADD COLUMN IF NOT EXISTS "iam_client" UUID
                    REFERENCES "iam_clients" ("uuid")
                        ON DELETE RESTRICT
                        ON UPDATE RESTRICT;
            """,
            """
                CREATE TABLE IF NOT EXISTS "iam_idp_authorization_info" (
                    "uuid" UUID PRIMARY KEY,
                    "idp" UUID NOT NULL REFERENCES "iam_idp" ("uuid"),
                    "state" VARCHAR(256) NOT NULL,
                    "response_type" VARCHAR(20) NOT NULL DEFAULT 'code'
                        CHECK (
                            response_type IN ('code')
                        ),
                    "nonce" VARCHAR(256) NOT NULL,
                    "scope" VARCHAR(256) NOT NULL,
                    "expiration_time_at" TIMESTAMP(6) NOT NULL,
                    "token" UUID DEFAULT NULL REFERENCES "iam_tokens" ("uuid"),
                    "code" UUID NOT NULL,
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
            """
                ALTER TABLE "iam_tokens"
                ADD COLUMN IF NOT EXISTS "nonce" VARCHAR(256) DEFAULT NULL;
            """,
            """
                ALTER TABLE "iam_clients"
                ADD COLUMN IF NOT EXISTS "signature_algorithm" JSONB
                    NOT NULL DEFAULT
                        '{"kind": "HS256", "secret_uuid": "00000000-0000-0000-0000-000000000001", "previous_secret_uuid": null}'::jsonb;
            """,
            """
                ALTER TABLE "iam_clients"
                DROP COLUMN IF EXISTS "redirect_url";
            """,
            """
                UPDATE "iam_clients"
                SET "salt" = 'd4JJ9QYuEEJxHCFja9FZskG4'
                WHERE "salt" = '5fOuZXeIn5e5TJlo9Pv5T219'; --fix incorrect default salt
            """,
            """
                ALTER TABLE "iam_tokens"
                ADD COLUMN IF NOT EXISTS "iam_client" UUID
                    REFERENCES "iam_clients" ("uuid")
                        ON DELETE CASCADE
                        ON UPDATE CASCADE;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

        session.execute("""
                INSERT INTO "secret_passwords" (
                    "uuid",
                    "name",
                    "description",
                    "project_id",
                    "constructor",
                    "method",
                    "value",
                    "status"
                ) VALUES (
                    '00000000-0000-0000-0000-000000000001',
                    'iam-client-hs256-secret',
                    'Default HS256 secret for IAM clients',
                    '00000000-0000-0000-0000-000000000000',
                    '{"kind": "plain"}'::jsonb,
                    'MANUAL',
                    'secret',
                    'ACTIVE'
                ) ON CONFLICT ("uuid") DO NOTHING;
            """)

        session.execute(
            """
                UPDATE "iam_tokens"
                SET "iam_client" = %s
                WHERE "iam_client" IS NULL;
            """,
            (_DEFAULT_IAM_CLIENT_UUID,),
        )

        expressions = [
            """
                ALTER TABLE "iam_tokens"
                ALTER COLUMN "iam_client" SET NOT NULL;
            """,
            """
                CREATE INDEX IF NOT EXISTS "iam_tokens_iam_client_idx"
                    ON "iam_tokens" ("iam_client");
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                DROP INDEX IF EXISTS "iam_tokens_iam_client_idx";
            """,
            """
                ALTER TABLE "iam_tokens"
                DROP COLUMN IF EXISTS "iam_client";
            """,
            """
                ALTER TABLE "iam_clients"
                ADD COLUMN IF NOT EXISTS "redirect_url" VARCHAR(256)
                    NOT NULL DEFAULT 'http://127.0.0.1:11010/v1/';
            """,
            """
                ALTER TABLE "iam_clients"
                DROP COLUMN IF EXISTS "signature_algorithm";
            """,
            """
                ALTER TABLE "iam_tokens"
                DROP COLUMN IF EXISTS "nonce";
            """,
            """
                ALTER TABLE "iam_idp"
                DROP COLUMN IF EXISTS "iam_client";
            """,
        ]

        for expression in expressions:
            session.execute(expression)

        self._delete_table_if_exists(session, "iam_idp_authorization_info")

        expressions = [
            """
                ALTER TABLE iam_idp
                ADD COLUMN IF NOT EXISTS well_known_endpoint VARCHAR(256)
                    NOT NULL DEFAULT '';
            """,
            """
                ALTER TABLE iam_idp
                RENAME COLUMN callback_uri TO redirect_uri_template;
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
