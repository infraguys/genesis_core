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
        self._depends = ["0014-network-ipam-067981.py"]

    @property
    def migration_id(self):
        return "8b38d350-ccf2-4af5-b2e1-0573b19ee363"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE "iam_users"
                ADD COLUMN "email_verified" BOOLEAN NOT NULL
                    DEFAULT FALSE,
                ADD COLUMN "confirmation_code" UUID NULL
                    DEFAULT NULL;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr)

    def downgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE "iam_users" DROP COLUMN IF EXISTS
                email_verified;
            """,
            """
            ALTER TABLE "iam_users" DROP COLUMN IF EXISTS
                confirmation_code;
            """,
        ]

        for expr in sql_expressions:
            session.execute(expr)


migration_step = MigrationStep()
