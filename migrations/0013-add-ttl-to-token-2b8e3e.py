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
        self._depends = ["0012-compute-permissions-aac851.py"]

    @property
    def migration_id(self):
        return "2b8e3e4d-6164-42ee-b0fe-3fd4d2c6dc81"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        session.execute(
            """
            ALTER TABLE "iam_tokens"
            ADD COLUMN expiration_delta FLOAT NOT NULL
                DEFAULT 900.0;
        """
        )
        session.execute(
            """
            ALTER TABLE "iam_tokens"
            ADD COLUMN refresh_expiration_delta FLOAT NOT NULL
                DEFAULT 86400.0;
        """
        )

    def downgrade(self, session):
        session.execute(
            'ALTER TABLE "iam_tokens" DROP COLUMN expiration_delta;'
        )
        session.execute(
            'ALTER TABLE "iam_tokens" DROP COLUMN refresh_expiration_delta;'
        )


migration_step = MigrationStep()
