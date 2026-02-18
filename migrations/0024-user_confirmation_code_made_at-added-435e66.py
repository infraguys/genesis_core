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
        self._depends = ["0023-nullable_fio-c9cb3a.py"]

    @property
    def migration_id(self):
        return "435e66ec-1fa8-4394-bc43-c7aaf54d0e78"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute("""
            ALTER TABLE iam_users
            ADD COLUMN confirmation_code_made_at TIMESTAMP NULL DEFAULT NULL;
        """)

    def downgrade(self, session):
        session.execute("""
            ALTER TABLE iam_users 
            DROP COLUMN confirmation_code_made_at;
        """)


migration_step = MigrationStep()
