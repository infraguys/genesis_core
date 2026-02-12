# Copyright 2026 Genesis Corporation
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
        self._depends = [
            "0049-lb-add-proxy-protocol-from-ef8f58.py",
        ]

    @property
    def migration_id(self):
        return "6c071d83-8fdf-45f3-90aa-cfde1898d3f7"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "compute_ports"
                    ADD COLUMN IF NOT EXISTS "source" VARCHAR(128) NULL
                    DEFAULT NULL;
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "compute_ports"
                    DROP COLUMN IF EXISTS "source";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
