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

import logging
import os

from gcl_sdk import migrations as sdk_migrations

from restalchemy.storage.sql import migrations

SDK_MIGRATION_FILE_NAME = "0003-ua-addtional-hashes-6e9ca8"


LOG = logging.getLogger(__name__)


class MigrationEngine(migrations.MigrationEngine):
    def apply_migration(self, migration_name, session):
        filename = self.get_file_name(migration_name)
        self._init_migration_table(session)
        migrations = self._load_migration_controllers(session)

        migration = migrations[filename]
        if migration.is_applied():
            LOG.warning("Migration '%s' is already applied", migration.name)
        else:
            LOG.info("Applying migration '%s'", migration.name)
            migrations[filename].apply(session, migrations)

    def rollback_migration(self, migration_name, session):
        filename = self.get_file_name(migration_name)
        self._init_migration_table(session)
        migrations = self._load_migration_controllers(session)
        migration = migrations[filename]
        if not migration.is_applied():
            LOG.warning("Migration '%s' is not applied", migration.name)
        else:
            LOG.info("Rolling back migration '%s'", migration.name)
            migrations[filename].rollback(session, migrations)


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0028-add-api-version-to-manifest-8de907.py"]

    @property
    def migration_id(self):
        return "c2c52a97-b1c2-44d1-a57f-1add51f219c2"

    @property
    def is_manual(self):
        return False

    def _get_migration_engine(self):
        sdk_migration_path = os.path.dirname(sdk_migrations.__file__)
        return MigrationEngine(migrations_path=sdk_migration_path)

    def upgrade(self, session):
        migration_engine = self._get_migration_engine()
        migration_engine.apply_migration(SDK_MIGRATION_FILE_NAME, session)

    def downgrade(self, session):
        migration_engine = self._get_migration_engine()
        migration_engine.rollback_migration(SDK_MIGRATION_FILE_NAME, session)


migration_step = MigrationStep()
