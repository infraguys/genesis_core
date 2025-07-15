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
        self._depends = ["0021-dns-permissions-7adac7.py"]

    @property
    def migration_id(self):
        return "fcf9b5f7-c351-43e4-af94-f73cef52472d"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        # Migration to make first_name and last_name nullable in iam_users table
        session.execute(
            """
            ALTER TABLE "iam_users"
            ALTER COLUMN "first_name" DROP NOT NULL,
            ALTER COLUMN "last_name" DROP NOT NULL;
            """
        )

    def downgrade(self, session):
        # Reverse migration to make first_name and last_name NOT NULL with empty string default
        session.execute(
            """
            -- First update any existing NULL values to empty string
            UPDATE "iam_users" 
            SET "first_name" = '' 
            WHERE "first_name" IS NULL;
            
            UPDATE "iam_users" 
            SET "last_name" = '' 
            WHERE "last_name" IS NULL;
            
            -- Then alter the columns to be NOT NULL
            ALTER TABLE "iam_users" 
            ALTER COLUMN "first_name" SET NOT NULL,
            ALTER COLUMN "last_name" SET NOT NULL;
            """
        )


migration_step = MigrationStep()
