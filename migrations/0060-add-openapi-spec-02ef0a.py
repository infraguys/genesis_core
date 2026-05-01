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


class MigrationStep(migrations.AbstractMigrationStep):
    def __init__(self):
        self._depends = ["0059-dns-sync-to-ecosystem-secret-len-a7b3c1.py"]

    @property
    def migration_id(self):
        return "02ef0abb-c4ab-4d7b-86a6-e8f847df64d4"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE
                    em_manifests
                ADD COLUMN IF NOT EXISTS
                    openapi_spec VARCHAR(2048) NULL DEFAULT NULL;
            """,
            """
                ALTER TABLE
                    em_elements
                ADD COLUMN IF NOT EXISTS
                    manifest UUID NULL DEFAULT NULL references em_manifests(uuid) ON DELETE RESTRICT;
            """,
            """
                UPDATE em_elements
                SET manifest = em_manifests.uuid
                FROM em_manifests
                WHERE em_elements.uuid = em_manifests.uuid
                  AND em_elements.manifest IS NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE em_manifests DROP COLUMN IF EXISTS
                    openapi_spec;
            """,
            """
                ALTER TABLE em_elements DROP COLUMN IF EXISTS
                    manifest;
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
