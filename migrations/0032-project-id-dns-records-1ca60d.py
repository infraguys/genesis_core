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
        self._depends = ["0031-node-set-permissions-2de46e.py"]

    @property
    def migration_id(self):
        return "1ca60d51-f2d1-49d5-b0ed-273d76492d6d"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            ALTER TABLE dns_records ADD COLUMN IF NOT EXISTS project_id UUID;
            
            UPDATE dns_records dr 
                SET project_id = dd.project_id 
            FROM dns_domains dd 
                WHERE dr.domain = dd.uuid 
                AND dr.project_id IS NULL;
            
            ALTER TABLE dns_records ALTER COLUMN project_id SET NOT NULL;
            """,
            """
            CREATE INDEX IF NOT EXISTS dns_records_project_id_idx
                ON dns_records (project_id);
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = [
            """
            DROP INDEX IF EXISTS dns_records_project_id_idx;
            """,
            """
            ALTER TABLE dns_records DROP COLUMN IF EXISTS project_id;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
