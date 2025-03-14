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
        self._depends = ["0009-node-builder-entities-0d8f66.py"]

    @property
    def migration_id(self):
        return "31471a63-e61d-4fa6-8bec-bb555e0f38c3"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE machines 
                ADD IF NOT EXISTS image varchar(255) NULL DEFAULT NULL;
            """
        ]

        for expr in sql_expressions:
            session.execute(expr, None)

    def downgrade(self, session):
        sql_expressions = [
            """
            ALTER TABLE machines 
                DROP COLUMN IF EXISTS image;
            """
        ]

        for expr in sql_expressions:
            session.execute(expr, None)


migration_step = MigrationStep()
