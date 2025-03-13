# Copyright 2025 Genesis Corporation
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


# NOTE(efrolov): copy-pasted from constants. Migration should have the
#                same values for autonomous working.
# Genesis Core Organization and Project Information
GENESIS_CORE_ORGANIZATION_ID = "11111111-1111-1111-1111-111111111111"
GENESIS_CORE_ORGANIZATION_NAME = "Genesis Corporation"
GENESIS_CORE_ORGANIZATION_DESCRIPTION = (
    "The organization serves as the central platform for all services"
    " and elements developed by Genesis Corporation."
)


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0005-add-organization-info-4fac91.py"]

    @property
    def migration_id(self):
        return "678510e9-1e83-4270-9cfc-ce5c5d09f960"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        insert_query = f"""
            INSERT INTO "iam_organizations" (
                "uuid", "name", "description"
            ) VALUES (
                '{GENESIS_CORE_ORGANIZATION_ID}',
                '{GENESIS_CORE_ORGANIZATION_NAME}',
                '{GENESIS_CORE_ORGANIZATION_DESCRIPTION}'
            );
        """
        session.execute(insert_query)

    def downgrade(self, session):
        delete_query = f"""
            DELETE FROM "iam_organizations"
            WHERE "uuid" = '{GENESIS_CORE_ORGANIZATION_ID}';
        """
        session.execute(delete_query)


migration_step = MigrationStep()
