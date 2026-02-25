# Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0010-image-for-machine-31471a.py"]

    @property
    def migration_id(self):
        return "ea974b0f-e5d0-4e17-8543-3770eca8df85"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute("""
            ALTER TABLE "iam_users"
            ADD COLUMN surname VARCHAR(128) NOT NULL DEFAULT ''
        """)
        session.execute("""
            ALTER TABLE "iam_users"
            ADD COLUMN phone VARCHAR(15)
        """)

    def downgrade(self, session):
        session.execute("""
            ALTER TABLE "iam_users"
            DROP COLUMN surname
        """)
        session.execute("""
            ALTER TABLE "iam_users"
            DROP COLUMN phone
        """)


migration_step = MigrationStep()
