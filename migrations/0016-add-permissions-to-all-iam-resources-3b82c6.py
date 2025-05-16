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


PERMISSION_PROJECT_LIST_ALL = "iam.project.list_all"
PERMISSION_PROJECT_READ_ALL = "iam.project.read_all"
PERMISSION_PROJECT_WRITE_ALL = "iam.project.write_all"
PERMISSION_PROJECT_DELETE_ALL = "iam.project.delete_all"

PERMISSION_PERMISSION_CREATE = "iam.permission.create"
PERMISSION_PERMISSION_READ = "iam.permission.read"
PERMISSION_PERMISSION_UPDATE = "iam.permission.update"
PERMISSION_PERMISSION_DELETE = "iam.permission.delete"


PERMISSION_PERMISSION_BINDING_CREATE = "iam.permission_binding.create"
PERMISSION_PERMISSION_BINDING_READ = "iam.permission_binding.read"
PERMISSION_PERMISSION_BINDING_UPDATE = "iam.permission_binding.update"
PERMISSION_PERMISSION_BINDING_DELETE = "iam.permission_binding.delete"


PERMISSION_ROLE_CREATE = "iam.role.create"
PERMISSION_ROLE_READ = "iam.role.read"
PERMISSION_ROLE_UPDATE = "iam.role.write"
PERMISSION_ROLE_DELETE = "iam.role.delete"


PERMISSION_ROLE_BINDING_CREATE = "iam.role_binding.create"
PERMISSION_ROLE_BINDING_READ = "iam.role_binding.read"
PERMISSION_ROLE_BINDING_UPDATE = "iam.role_binding.update"
PERMISSION_ROLE_BINDING_DELETE = "iam.role_binding.delete"


PERMISSION_IAM_CLIENT_CREATE = "iam.iam_client.create"
PERMISSION_IAM_CLIENT_READ_ALL = "iam.iam_client.read_all"
PERMISSION_IAM_CLIENT_UPDATE = "iam.iam_client.update"
PERMISSION_IAM_CLIENT_DELETE = "iam.iam_client.delete"


NAMESPACE_UUID = uuid.UUID("a6c4c7a8-b1d2-4e8f-9a3c-1d7e4f5a9b0c")


def generate_uuid(name):
    return str(uuid.uuid5(NAMESPACE_UUID, name))


PERMISSION_UUIDS = {
    PERMISSION_PROJECT_LIST_ALL: generate_uuid(PERMISSION_PROJECT_LIST_ALL),
    PERMISSION_PROJECT_READ_ALL: generate_uuid(PERMISSION_PROJECT_READ_ALL),
    PERMISSION_PROJECT_WRITE_ALL: generate_uuid(PERMISSION_PROJECT_WRITE_ALL),
    PERMISSION_PROJECT_DELETE_ALL: generate_uuid(
        PERMISSION_PROJECT_DELETE_ALL
    ),
    PERMISSION_PERMISSION_CREATE: generate_uuid(PERMISSION_PERMISSION_CREATE),
    PERMISSION_PERMISSION_READ: generate_uuid(PERMISSION_PERMISSION_READ),
    PERMISSION_PERMISSION_UPDATE: generate_uuid(PERMISSION_PERMISSION_UPDATE),
    PERMISSION_PERMISSION_DELETE: generate_uuid(PERMISSION_PERMISSION_DELETE),
    PERMISSION_PERMISSION_BINDING_CREATE: generate_uuid(
        PERMISSION_PERMISSION_BINDING_CREATE
    ),
    PERMISSION_PERMISSION_BINDING_READ: generate_uuid(
        PERMISSION_PERMISSION_BINDING_READ
    ),
    PERMISSION_PERMISSION_BINDING_UPDATE: generate_uuid(
        PERMISSION_PERMISSION_BINDING_UPDATE
    ),
    PERMISSION_PERMISSION_BINDING_DELETE: generate_uuid(
        PERMISSION_PERMISSION_BINDING_DELETE
    ),
    PERMISSION_ROLE_CREATE: generate_uuid(PERMISSION_ROLE_CREATE),
    PERMISSION_ROLE_READ: generate_uuid(PERMISSION_ROLE_READ),
    PERMISSION_ROLE_UPDATE: generate_uuid(PERMISSION_ROLE_UPDATE),
    PERMISSION_ROLE_DELETE: generate_uuid(PERMISSION_ROLE_DELETE),
    PERMISSION_ROLE_BINDING_CREATE: generate_uuid(
        PERMISSION_ROLE_BINDING_CREATE
    ),
    PERMISSION_ROLE_BINDING_READ: generate_uuid(PERMISSION_ROLE_BINDING_READ),
    PERMISSION_ROLE_BINDING_UPDATE: generate_uuid(
        PERMISSION_ROLE_BINDING_UPDATE
    ),
    PERMISSION_ROLE_BINDING_DELETE: generate_uuid(
        PERMISSION_ROLE_BINDING_DELETE
    ),
    PERMISSION_IAM_CLIENT_CREATE: generate_uuid(PERMISSION_IAM_CLIENT_CREATE),
    PERMISSION_IAM_CLIENT_READ_ALL: generate_uuid(
        PERMISSION_IAM_CLIENT_READ_ALL
    ),
    PERMISSION_IAM_CLIENT_UPDATE: generate_uuid(PERMISSION_IAM_CLIENT_UPDATE),
    PERMISSION_IAM_CLIENT_DELETE: generate_uuid(PERMISSION_IAM_CLIENT_DELETE),
}


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = ["0015-add-email-confirmation-info-8b38d3.py"]

    @property
    def migration_id(self):
        return "3b82c606-7f77-49ff-8bbf-d04112569117"

    def _create_permissions(self, session):
        permissions = [
            # User permissions
            (
                PERMISSION_PROJECT_LIST_ALL,
                "Allows listing projects in the system",
            ),
            (
                PERMISSION_PROJECT_READ_ALL,
                "Allows reading all project details",
            ),
            (
                PERMISSION_PROJECT_WRITE_ALL,
                "Allows modifying any project`s data",
            ),
            (PERMISSION_PROJECT_DELETE_ALL, "Allows deleting any project"),
            (PERMISSION_PERMISSION_CREATE, "Allows creating new permissions"),
            (PERMISSION_PERMISSION_READ, "Allows reading permissions"),
            (
                PERMISSION_PERMISSION_UPDATE,
                "Allows updating existing permissions",
            ),
            (PERMISSION_PERMISSION_DELETE, "Allows deleting permissions"),
            (
                PERMISSION_PERMISSION_BINDING_CREATE,
                "Allows creating permission bindings",
            ),
            (
                PERMISSION_PERMISSION_BINDING_READ,
                "Allows reading permission bindings",
            ),
            (
                PERMISSION_PERMISSION_BINDING_UPDATE,
                "Allows updating permission bindings",
            ),
            (
                PERMISSION_PERMISSION_BINDING_DELETE,
                "Allows deleting permission bindings",
            ),
            (PERMISSION_ROLE_CREATE, "Allows creating new roles"),
            (PERMISSION_ROLE_READ, "Allows reading roles"),
            (PERMISSION_ROLE_UPDATE, "Allows updating existing roles"),
            (PERMISSION_ROLE_DELETE, "Allows deleting roles"),
            (PERMISSION_ROLE_BINDING_CREATE, "Allows creating role bindings"),
            (PERMISSION_ROLE_BINDING_READ, "Allows reading role bindings"),
            (PERMISSION_ROLE_BINDING_UPDATE, "Allows updating role bindings"),
            (PERMISSION_ROLE_BINDING_DELETE, "Allows deleting role bindings"),
            (PERMISSION_IAM_CLIENT_CREATE, "Allows creating IAM clients"),
            (PERMISSION_IAM_CLIENT_READ_ALL, "Allows reading all IAM clients"),
            (PERMISSION_IAM_CLIENT_UPDATE, "Allows updating IAM clients"),
            (PERMISSION_IAM_CLIENT_DELETE, "Allows deleting IAM clients"),
        ]

        for name, description in permissions:
            session.execute(
                f"""
                INSERT INTO iam_permissions (
                    uuid, name, description
                ) VALUES (
                    '{PERMISSION_UUIDS[name]}',
                    '{name}',
                    '{description}'
                )
                ON CONFLICT (uuid) DO NOTHING;
            """
            )

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        self._create_permissions(session)

    def _delete_permissions(self, session):
        for permission_uuid in PERMISSION_UUIDS.values():
            session.execute(
                f"""
                DELETE FROM iam_permissions
                WHERE uuid = '{permission_uuid}';
            """
            )

    def downgrade(self, session):
        self._delete_permissions(session)


migration_step = MigrationStep()
