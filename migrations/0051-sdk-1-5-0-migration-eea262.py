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
from gcl_sdk.common import utils as sdk_utils

from restalchemy.storage.sql import migrations

SDK_MIGRATION_FILE_NAME = "0005-ua-api-encryption-keys-2f8d3a"


LOG = logging.getLogger(__name__)


class MigrationStep(migrations.AbstractMigrationStep):

    def __init__(self):
        self._depends = ["0050-subnet-source-6c071d.py"]

    @property
    def migration_id(self):
        return "eea262b3-ec9f-4547-964b-5801857fd5ee"

    @property
    def is_manual(self):
        return False

    def _get_migration_engine(self):
        sdk_migration_path = os.path.dirname(sdk_migrations.__file__)
        return sdk_utils.MigrationEngine(migrations_path=sdk_migration_path)

    def upgrade(self, session):
        migration_engine = self._get_migration_engine()
        migration_engine.apply_migration(SDK_MIGRATION_FILE_NAME, session)

    def downgrade(self, session):
        migration_engine = self._get_migration_engine()
        migration_engine.rollback_migration(SDK_MIGRATION_FILE_NAME, session)


migration_step = MigrationStep()
