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
        self._depends = ["0025-secret-ssh-keys-ad3fad.py"]

    @property
    def migration_id(self):
        return "41f4b995-d237-4b89-bec9-046a50de8d27"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expression = """
            DROP INDEX IF EXISTS iam_users_name_idx;
            CREATE UNIQUE INDEX iam_users_name_lower_idx ON iam_users (
                LOWER(name)
            );
        """
        session.execute(expression)

    def downgrade(self, session):
        expression = """
            DROP INDEX IF EXISTS iam_users_name_lower_idx;
            CREATE UNIQUE INDEX iam_users_name_idx ON iam_users (name);
        """
        session.execute(expression)


migration_step = MigrationStep()
