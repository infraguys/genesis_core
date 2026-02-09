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
#
import os

from gcl_sdk import migrations as sdk_migrations
from gcl_sdk.common import utils as sdk_utils
from restalchemy.storage.sql import migrations

SDK_MIGRATION_FILE_NAME = "0005-ua-api-encryption-keys-2f8d3a.py"


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = [
            "0048-iam-nonce-optional-c6e9f6.py",
        ]

    @property
    def migration_id(self):
        return "9c8d45c2-4c2d-46c8-9d2c-5b7d77f0e76b"

    @property
    def is_manual(self):
        return False

    def _get_migration_engine(self):
        sdk_migration_path = os.path.dirname(sdk_migrations.__file__)
        return sdk_utils.MigrationEngine(migrations_path=sdk_migration_path)

    def upgrade(self, session):
        migration_engine = self._get_migration_engine()
        migration_engine.apply_migration(SDK_MIGRATION_FILE_NAME, session)

        expressions = [
            """
            ALTER TABLE ua_node_encryption_keys
                DROP CONSTRAINT IF EXISTS ua_node_encryption_keys_uuid_fkey;
            """,
            """
            ALTER TABLE ua_node_encryption_keys
                ADD CONSTRAINT ua_node_encryption_keys_uuid_fkey
                FOREIGN KEY (uuid)
                REFERENCES nodes(uuid)
                ON DELETE CASCADE;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

    def downgrade(self, session):
        migration_engine = self._get_migration_engine()
        expressions = [
            """
            ALTER TABLE ua_node_encryption_keys
                DROP CONSTRAINT IF EXISTS ua_node_encryption_keys_uuid_fkey;
            """,
        ]

        for expression in expressions:
            session.execute(expression, None)

        migration_engine.rollback_migration(SDK_MIGRATION_FILE_NAME, session)


migration_step = MigrationStep()
