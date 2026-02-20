#    Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
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
        self._depends = ["0036-init-services-741b72.py"]

    @property
    def migration_id(self):
        return "815825d7-4864-4a0d-badc-2b186925771d"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """
            CREATE INDEX IF NOT EXISTS em_imports_element_idx
                ON em_imports (element);
            """,
            """
            ALTER TABLE em_imports
            ADD CONSTRAINT em_imports_unique_name UNIQUE (element, name);
            """,
            """
            CREATE INDEX IF NOT EXISTS em_exports_element_idx
                ON em_exports (element);
            """,
            """
            ALTER TABLE em_exports
            ADD CONSTRAINT em_exports_unique_name UNIQUE (element, name);
            """,
            """
            CREATE INDEX IF NOT EXISTS em_resources_element_idx
                ON em_resources (element);
            """,
            """
            ALTER TABLE em_elements
            ADD CONSTRAINT em_elements_unique_name UNIQUE (name);
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):

        expressions = [
            """
            DROP INDEX IF EXISTS em_imports_element_idx;
            """,
            """
            ALTER TABLE em_imports
            DROP CONSTRAINT em_imports_unique_name;
            """,
            """
            DROP INDEX IF EXISTS em_exports_element_idx;
            """,
            """
            ALTER TABLE em_exports
            DROP CONSTRAINT em_exports_unique_name;
            """,
            """
            DROP INDEX IF EXISTS em_resources_element_idx;
            """,
            """
            ALTER TABLE em_elements
            DROP CONSTRAINT em_elements_unique_name;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)


migration_step = MigrationStep()
