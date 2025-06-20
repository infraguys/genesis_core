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

import logging
import os

from gcl_sdk import migrations as sdk_migrations

from restalchemy.storage.sql import migrations


SDK_MIGRATION_FILE_NAME = "0001-universal-agent-391c09.py"


LOG = logging.getLogger(__name__)


class MigrationEngine(migrations.MigrationEngine):

    def apply_migration(self, migration_name, session):
        filename = self.get_file_name(migration_name)
        self._init_migration_table(session)
        migrations = self._load_migration_controllers(session)

        migration = migrations[filename]
        if migration.is_applied():
            LOG.warning("Migration '%s' is already applied", migration.name)
        else:
            LOG.info("Applying migration '%s'", migration.name)
            migrations[filename].apply(session, migrations)

    def rollback_migration(self, migration_name, session):
        filename = self.get_file_name(migration_name)
        self._init_migration_table(session)
        migrations = self._load_migration_controllers(session)
        migration = migrations[filename]
        if not migration.is_applied():
            LOG.warning("Migration '%s' is not applied", migration.name)
        else:
            LOG.info("Rolling back migration '%s'", migration.name)
            migrations[filename].rollback(session, migrations)


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0017-init-configs-c3bbc6.py"]

    @property
    def migration_id(self):
        return "76bca4a1-46ab-495e-b956-99bdab62d7c5"

    @property
    def is_manual(self):
        return False

    def _get_migration_engine(self):
        sdk_migration_path = os.path.dirname(sdk_migrations.__file__)
        return MigrationEngine(migrations_path=sdk_migration_path)

    def upgrade(self, session):
        expressions = [
            """
                CREATE TABLE IF NOT EXISTS "em_manifests" (
                    "uuid" UUID PRIMARY KEY,
                    "name" VARCHAR(255) NOT NULL,
                    "description" VARCHAR(255) NOT NULL DEFAULT '',
                    "status" VARCHAR(20) NOT NULL DEFAULT 'NEW'
                        CHECK (
                            status IN (
                                'ACTIVE'
                            )
                        ),
                    "version" VARCHAR(64) NOT NULL,
                    "schema_version" INTEGER NOT NULL DEFAULT 1,
                    "project_id" UUID NOT NULL,
                    "requirements" JSONB NOT NULL DEFAULT '{}',
                    "resources" JSONB NOT NULL DEFAULT '{}',
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS "em_elements" (
                    "uuid" UUID PRIMARY KEY,
                    "name" VARCHAR(255) NOT NULL,
                    "description" VARCHAR(255) NOT NULL DEFAULT '',
                    "status" VARCHAR(20) NOT NULL DEFAULT 'NEW'
                        CHECK (
                            status IN (
                                'NEW',
                                'IN_PROGRESS',
                                'ACTIVE'
                            )
                        ),
                    "version" VARCHAR(64) NOT NULL,
                    "install_type" VARCHAR(20) NOT NULL DEFAULT 'MANUAL'
                        CHECK (
                            install_type IN (
                                'MANUAL',
                                'AUTO_AS_DEPENDENCY'
                            )
                        ),
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    CONSTRAINT unique_em_elements_name_version_idx UNIQUE (
                        name, version
                    )
                );
            """,
            """
                CREATE TABLE IF NOT EXISTS "em_resources" (
                    "uuid" UUID PRIMARY KEY,
                    "name" VARCHAR(255) NOT NULL,
                    "element" UUID NOT NULL REFERENCES em_elements("uuid")
                        ON DELETE CASCADE,
                    "status" VARCHAR(20) NOT NULL DEFAULT 'NEW'
                        CHECK (
                            status IN (
                                'NEW',
                                'IN_PROGRESS',
                                'ACTIVE'
                            )
                        ),
                    "resource_link_prefix" VARCHAR(256) NOT NULL,
                    "value" JSONB NOT NULL DEFAULT '{}',
                    "target_resource" UUID DEFAULT NULL REFERENCES
                        ua_target_resources("res_uuid"),
                    "actual_resource" UUID DEFAULT NULL REFERENCES
                        ua_actual_resources("res_uuid"),
                    "full_hash" VARCHAR(256) NOT NULL DEFAULT '',
                    "created_at" TIMESTAMP(6) NOT NULL DEFAULT NOW(),
                    "updated_at" TIMESTAMP(6) NOT NULL DEFAULT NOW()
                );
            """,
            """
                CREATE OR REPLACE VIEW "em_incorrect_statuses_view" AS
                WITH "em_incorrect_resource_statuses" AS (
                    WITH "tmp" AS (
                        SELECT
                            "element",
                            BOOL_OR("status" = 'IN_PROGRESS') AS
                                "has_in_progress",
                            BOOL_AND("status" = 'ACTIVE') AS "all_active",
                            BOOL_AND("status" = 'NEW') AS "all_new",
                            COUNT(*) AS "resources_count"
                        FROM "em_resources"
                        GROUP BY "element"
                    )
                    SELECT
                        "e"."uuid" "uuid",
                        "e"."name" "name",
                        "e"."status" "api_status",
                        CASE
                            WHEN "tmp"."resources_count" IS NULL THEN 'ACTIVE'
                            WHEN "tmp"."has_in_progress" THEN 'IN_PROGRESS'
                            WHEN "tmp"."all_active" THEN 'ACTIVE'
                            WHEN "tmp"."all_new" THEN 'NEW'
                            ELSE 'IN_PROGRESS'
                        END AS "actual_status"
                    FROM "em_elements" "e"
                    LEFT JOIN "tmp" "tmp" ON "e"."uuid" = "tmp"."element"
                )
                SELECT * FROM "em_incorrect_resource_statuses" "eis"
                WHERE "eis"."api_status" != "eis"."actual_status";
            """,
            """
                CREATE OR REPLACE VIEW "em_outdated_resources_view" AS
                SELECT
                    COALESCE("er"."uuid", "utr"."uuid") AS "uuid",
                    "er"."uuid" AS "em_resource",
                    "utr"."res_uuid" AS "target_resource"
                FROM "em_resources" "er"
                FULL OUTER JOIN  (
                    SELECT
                        "uuid",
                        "res_uuid",
                        "updated_at",
                        "tracked_at"
                    FROM "ua_target_resources"
                    WHERE "kind" like 'em_core_%'
                ) AS "utr"
                    on "er"."uuid" = "utr"."uuid"
                WHERE
                    "er"."uuid"  IS NULL
                    OR "utr"."uuid" IS NULL
                    OR "er"."updated_at" <> "utr"."tracked_at";
            """,
            """
                CREATE OR REPLACE VIEW "em_incorrect_resource_statuses_view" AS
                SELECT
                    "er"."uuid" AS "uuid",
                    "er"."status" AS "current_status",
                    "uar"."status" AS "actual_status"
                FROM
                    "em_resources" "er"
                LEFT JOIN (
                    SELECT
                        "uuid",
                        "status"
                    FROM "ua_actual_resources"
                    WHERE "kind" like 'em_core_%'
                ) AS "uar"
                ON
                    "er"."uuid" = "uar"."uuid"
                WHERE
                    "er"."status" <> "uar"."status";
            """,
        ]

        migration_engine = self._get_migration_engine()
        migration_engine.apply_migration(SDK_MIGRATION_FILE_NAME, session)

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        tables = [
            "em_manifests",
            "em_elements",
            "em_resources",
        ]
        views = [
            "em_incorrect_statuses_view",
            "em_incorrect_resource_statuses_view",
            "em_outdated_resources_view",
        ]

        for view in reversed(views):
            self._delete_view_if_exists(session, view)

        for table in reversed(tables):
            self._delete_table_if_exists(session, table)

        migration_engine = self._get_migration_engine()
        migration_engine.rollback_migration(SDK_MIGRATION_FILE_NAME, session)


migration_step = MigrationStep()
