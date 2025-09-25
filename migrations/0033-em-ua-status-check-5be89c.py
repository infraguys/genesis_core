#    Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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
        self._depends = ["0032-project-id-dns-records-1ca60d.py"]

    @property
    def migration_id(self):
        return "5be89c1f-77e1-4054-ab9f-e4d961e9dda8"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
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
                    WHERE "kind" like 'em_%'
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
                    WHERE "kind" like 'em_%'
                ) AS "uar"
                ON
                    "er"."uuid" = "uar"."uuid"
                WHERE
                    "er"."status" <> "uar"."status";
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = [
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

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
