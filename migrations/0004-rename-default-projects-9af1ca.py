#    Copyright 2026 Genesis Corporation.
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

from exordos_core.common import constants

# The owner of a project is the user of its earliest OWNER role binding.
PROJECT_OWNERS = """
    SELECT DISTINCT ON (rb.project) rb.project AS project, u.name AS owner
    FROM public.iam_binding_roles rb
    JOIN public.iam_users u ON u.uuid = rb."user"
    WHERE rb.project IS NOT NULL AND rb.role = '{owner_role}'
    ORDER BY rb.project, rb.created_at
""".format(owner_role=constants.OWNER_ROLE_UUID)


class MigrationStep(migrations.AbstractMigrationStep):
    def __init__(self):
        self._depends = ["0003-add-tags-to-models-9e4b2d1f.py"]

    @property
    def migration_id(self):
        return "9af1ca82-0484-49f7-b385-3ac553419a9d"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        # iam_projects.name is varchar(128), so a long username is cut off.
        session.execute(
            f"""
            UPDATE public.iam_projects p
            SET name = left(o.owner || '''s project', 128),
                updated_at = now()
            FROM ({PROJECT_OWNERS}) o
            WHERE p.uuid = o.project AND p.name = 'default';
            """
        )

    def downgrade(self, session):
        session.execute(
            f"""
            UPDATE public.iam_projects p
            SET name = 'default',
                updated_at = now()
            FROM ({PROJECT_OWNERS}) o
            WHERE p.uuid = o.project
              AND p.name = left(o.owner || '''s project', 128);
            """
        )


migration_step = MigrationStep()
