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
        self._depends = ["0022-secret-certs-d340e8.py"]

    @property
    def migration_id(self):
        return "c9cb3a7d-28c9-4f8e-ba52-c2fd5f7c18a9"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expression = """
            ALTER TABLE iam_users 
            ALTER COLUMN first_name DROP NOT NULL,
            ALTER COLUMN last_name DROP NOT NULL;
        """
        session.execute(expression)

    def downgrade(self, session):
        expression = """
            BEGIN;
                UPDATE iam_users SET first_name = '' WHERE first_name IS NULL;
                UPDATE iam_users SET last_name = '' WHERE last_name IS NULL;
                ALTER TABLE iam_users 
                ALTER COLUMN first_name SET NOT NULL,
                ALTER COLUMN last_name SET NOT NULL;
            COMMIT;
        """
        session.execute(expression)


migration_step = MigrationStep()
