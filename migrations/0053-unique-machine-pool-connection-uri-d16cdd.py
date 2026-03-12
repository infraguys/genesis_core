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


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0052-iam-user-custom-props-bc80b5.py"]

    @property
    def migration_id(self):
        return "d16cddcf-b117-4a87-9ad7-8142925c23db"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
                CREATE OR REPLACE FUNCTION to_jsonb_safe(t TEXT) RETURNS jsonb AS $$
                BEGIN
                    RETURN t::jsonb;
                EXCEPTION
                    WHEN invalid_text_representation THEN
                        RETURN NULL;
                END;
                $$ LANGUAGE plpgsql IMMUTABLE
            """,
            """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    "machine_pools_connection_uri_unique_idx"
                    ON "machine_pools" ((to_jsonb_safe("driver_spec")->>'connection_uri'))
                    NULLS DISTINCT
            """,
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):
        expressions = [
            """
                DROP INDEX IF EXISTS
                    "machine_pools_connection_uri_unique_idx"
            """,
            """
                DROP FUNCTION IF EXISTS to_jsonb_safe
            """,
        ]

        for expression in expressions:
            session.execute(expression)


migration_step = MigrationStep()
