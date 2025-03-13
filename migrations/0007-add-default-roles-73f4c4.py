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


NEWCOMER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000001"
NEWCOMER_ROLE_NAME = "newcomer"
NEWCOMER_ROLE_DESCRIPTION = (
    "Default role for newly registered users. Provides basic system access "
    "and onboarding capabilities."
)

OWNER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000002"
OWNER_ROLE_NAME = "owner"
OWNER_ROLE_DESCRIPTION = (
    "Project ownership role. Grants full administrative privileges "
    "within a specific project. Automatically assigned during project "
    "creation process."
)


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0006-add-gc-organization-678510.py"]

    @property
    def migration_id(self):
        return "73f4c423-b617-4269-b9f2-6115050c8b6c"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        insert_queries = [
            f"""
            INSERT INTO "iam_roles" (
                "uuid", "name", "description", "project_id"
            ) VALUES (
                '{NEWCOMER_ROLE_UUID}',
                '{NEWCOMER_ROLE_NAME}',
                '{NEWCOMER_ROLE_DESCRIPTION}',
                NULL
            );
            """,
            f"""
            INSERT INTO "iam_roles" (
                "uuid", "name", "description", "project_id"
            ) VALUES (
                '{OWNER_ROLE_UUID}',
                '{OWNER_ROLE_NAME}',
                '{OWNER_ROLE_DESCRIPTION}',
                NULL
            );
            """,
        ]

        for query in insert_queries:
            session.execute(query)

    def downgrade(self, session):
        delete_queries = [
            f"DELETE FROM iam_roles WHERE uuid = '{NEWCOMER_ROLE_UUID}';",
            f"DELETE FROM iam_roles WHERE uuid = '{OWNER_ROLE_UUID}';",
        ]

        for query in delete_queries:
            session.execute(query)


migration_step = MigrationStep()
