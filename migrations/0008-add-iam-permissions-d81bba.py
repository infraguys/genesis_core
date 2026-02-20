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

import uuid
from restalchemy.storage.sql import migrations

USER_LIST = "iam.user.list"
USER_READ_ALL = "iam.user.read_all"
USER_WRITE_ALL = "iam.user.write_all"
USER_DELETE_ALL = "iam.user.delete_all"
USER_DELETE = "iam.user.delete"

ORG_CREATE = "iam.organization.create"
ORG_READ_ALL = "iam.organization.read_all"
ORG_WRITE_ALL = "iam.organization.write_all"
ORG_DELETE = "iam.organization.delete"
ORG_DELETE_ALL = "iam.organization.delete_all"


NAMESPACE_UUID = uuid.UUID("a6c4c7a8-b1d2-4e8f-9a3c-1d7e4f5a9b0c")


def generate_uuid(name):
    return str(uuid.uuid5(NAMESPACE_UUID, name))


PERMISSION_UUIDS = {
    USER_LIST: generate_uuid(USER_LIST),
    USER_READ_ALL: generate_uuid(USER_READ_ALL),
    USER_WRITE_ALL: generate_uuid(USER_WRITE_ALL),
    USER_DELETE_ALL: generate_uuid(USER_DELETE_ALL),
    USER_DELETE: generate_uuid(USER_DELETE),
    ORG_CREATE: generate_uuid(ORG_CREATE),
    ORG_READ_ALL: generate_uuid(ORG_READ_ALL),
    ORG_WRITE_ALL: generate_uuid(ORG_WRITE_ALL),
    ORG_DELETE: generate_uuid(ORG_DELETE),
    ORG_DELETE_ALL: generate_uuid(ORG_DELETE_ALL),
}

GENESIS_CORE_ORG_UUID = "11111111-1111-1111-1111-111111111111"
NEWCOMER_ROLE_UUID = "726f6c65-0000-0000-0000-000000000001"

IAM_PROJECT_UUID = generate_uuid("GenesisCore-IAM-Project")


class MigrationStep(migrations.AbstarctMigrationStep):
    def __init__(self):
        self._depends = ["0007-add-default-roles-73f4c4.py"]

    @property
    def migration_id(self):
        return "d81bba1e-eec5-44ba-b4f3-7a95e34bf1f7"

    @property
    def is_manual(self):
        return False

    def _create_permissions(self, session):
        permissions = [
            # User permissions
            (USER_LIST, "Allows listing users in the system"),
            (USER_READ_ALL, "Allows reading all user profiles"),
            (USER_WRITE_ALL, "Allows modifying any user`s data"),
            (USER_DELETE_ALL, "Allows deleting any user account"),
            (
                USER_DELETE,
                "Allows users to delete their own account",
            ),
            # Organization permissions
            (ORG_CREATE, "Allows creating new organizations"),
            (
                ORG_READ_ALL,
                "Allows viewing all organization details",
            ),
            (
                ORG_WRITE_ALL,
                "Allows modifying any organization`s data",
            ),
            (ORG_DELETE, "Allows deleting own organization"),
            (ORG_DELETE_ALL, "Allows deleting any organization"),
        ]

        for name, description in permissions:
            session.execute(f"""
                INSERT INTO iam_permissions (
                    uuid, name, description
                ) VALUES (
                    '{PERMISSION_UUIDS[name]}',
                    '{name}',
                    '{description}'
                )
                ON CONFLICT (uuid) DO NOTHING;
            """)

    def _create_iam_project(self, session):
        session.execute(f"""
            INSERT INTO iam_projects (
                uuid, name, description, organization
            ) VALUES (
                '{IAM_PROJECT_UUID}',
                'iam-core',
                'Identity and Access Management Core Project',
                '{GENESIS_CORE_ORG_UUID}'
            )
            ON CONFLICT (uuid) DO NOTHING;
        """)

    def _create_bindings(self, session):
        bind_permissions = [USER_DELETE, ORG_CREATE, ORG_DELETE]

        for perm_name in bind_permissions:
            session.execute(f"""
                INSERT INTO iam_binding_permissions (
                    uuid, role, permission, project_id
                ) VALUES (
                    gen_random_uuid(),
                    '{NEWCOMER_ROLE_UUID}',
                    '{PERMISSION_UUIDS[perm_name]}',
                    '{IAM_PROJECT_UUID}'
                );
            """)

    def upgrade(self, session):
        self._create_permissions(session)
        self._create_iam_project(session)
        self._create_bindings(session)

    def _delete_bindings(self, session):
        for permission_uuid in PERMISSION_UUIDS.values():
            session.execute(f"""
                DELETE FROM iam_binding_permissions
                WHERE
                    permission = '{permission_uuid}';
            """)

    def _delete_iam_project(self, session):
        session.execute(f"""
            DELETE FROM iam_projects
            WHERE uuid = '{IAM_PROJECT_UUID}';
        """)

    def _delete_permissions(self, session):
        for permission_uuid in PERMISSION_UUIDS.values():
            session.execute(f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{permission_uuid}';
            """)

    def downgrade(self, session):
        self._delete_bindings(session)
        self._delete_iam_project(session)
        self._delete_permissions(session)


migration_step = MigrationStep()
