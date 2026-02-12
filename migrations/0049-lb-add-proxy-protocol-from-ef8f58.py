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
            "0048-iam-nonce-optional-c6e9f6.py",
        ]

    @property
    def migration_id(self):
        return "ef8f58c7-1279-49db-9824-1e0aab090c0b"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                ALTER TABLE "net_lb_vhosts"
                    ADD COLUMN IF NOT EXISTS "proxy_protocol_from" VARCHAR(18);
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                ALTER TABLE "net_lb_vhosts"
                    DROP COLUMN IF EXISTS "proxy_protocol_from";
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
