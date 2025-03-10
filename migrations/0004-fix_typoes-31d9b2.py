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
        self._depends = ["0003-Organization-Roles-4b584d.py"]

    @property
    def migration_id(self):
        return "31d9b221-7af4-4bef-b769-c793e4eb1da0"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """\
                ALTER TABLE iam_tokens
                RENAME COLUMN experation_at TO expiration_at;
            """,
            """\
                ALTER TABLE iam_tokens
                RENAME COLUMN refresh_experation_at TO refresh_expiration_at;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """\
                ALTER TABLE iam_tokens
                RENAME COLUMN expiration_at TO experation_at;
            """,
            """\
                ALTER TABLE iam_tokens
                RENAME COLUMN refresh_expiration_at TO refresh_experation_at;
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
