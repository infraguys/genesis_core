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
from __future__ import annotations

import logging
import collections
import typing as tp
import uuid as sys_uuid

from restalchemy.common import contexts
from restalchemy.dm import filters as dm_filters
from gcl_looper.services import basic
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_core.secret.dm import models
from genesis_core.secret import constants as sc


LOG = logging.getLogger(__name__)


class SecretServiceBuilder(basic.BasicService):

    def _get_new_passwords(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[models.Password]:
        return models.Password.get_new_passwords(limit=limit)

    def _get_changed_passwords(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[models.Password]:
        return models.Password.get_updated_passwords(limit=limit)

    def _get_deleted_passwords(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[ua_models.TargetResource]:
        return models.Password.get_deleted_passwords(limit=limit)

    def _get_outdated_resources(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> dict[
        sys_uuid.UUID,  # Resource UUID
        tuple[ua_models.TargetResource, ua_models.Resource],
    ]:
        outdated = ua_models.OutdatedResource.objects.get_all(
            filters={"kind": dm_filters.EQ(sc.PASSWORD_KIND)},
            limit=limit,
        )
        return {
            pair.target_resource.uuid: (
                pair.target_resource,
                pair.actual_resource,
            )
            for pair in outdated
        }

    def _get_outdated_passwords(
        self, uuids: tp.Collection[sys_uuid.UUID]
    ) -> list[models.Password]:
        return models.Password.objects.get_all(
            filters={"uuid": dm_filters.In(str(p) for p in uuids)},
        )

    def _actualize_new_passwords(
        self, passwords: list[models.Password] | None = None
    ) -> None:
        """Actualize new passwords."""
        passwords = passwords or self._get_new_passwords()

        if len(passwords) == 0:
            return

        # Just create resources for new passwords
        for password in passwords:
            password_resource = password.to_ua_resource(sc.PASSWORD_KIND)
            try:
                password_resource.insert()
                password.status = sc.SecretStatus.IN_PROGRESS.value
                password.save()

                # TODO(akremenetsky): Improve this snippet in the future
                password_resource.tracked_at = password.updated_at
                password_resource.status = password.status
                password_resource.update()
                LOG.info(
                    "Password resource %s created", password_resource.uuid
                )
            except Exception:
                LOG.exception(
                    "Error creating password resource %s", password.uuid
                )

    def _actualize_changed_passwords(self) -> None:
        """Actualize passwords changed by user."""
        changed_passwords = {p.uuid: p for p in self._get_changed_passwords()}

        if len(changed_passwords) == 0:
            return

        password_resources = ua_models.TargetResource.objects.get_all(
            filters={
                "uuid": dm_filters.In(
                    str(p) for p in changed_passwords.keys()
                ),
                "kind": dm_filters.EQ(sc.PASSWORD_KIND),
            }
        )

        # Update every resource in accordance with the new password
        for resource in password_resources:
            password = changed_passwords[resource.uuid]
            new_resource = password.to_ua_resource(sc.PASSWORD_KIND)

            # Update the original resource
            resource.update_value(new_resource)
            try:
                password.status = sc.SecretStatus.IN_PROGRESS.value
                password.save()

                resource.tracked_at = password.updated_at
                resource.status = password.status
                resource.update()
                LOG.debug("Password resource %s updated", resource.uuid)
            except Exception:
                LOG.exception(
                    "Error updating password resource %s", resource.uuid
                )

    def _actualize_outdated_password(
        self,
        password: models.Password,
        target_resource: ua_models.TargetResource,
        actual_resource: ua_models.Resource,
    ) -> None:
        """Actualize outdated password."""
        password_updated = False
        saved_password = models.Password.from_ua_resource(actual_resource)

        # Actualize password
        if (
            saved_password.status != password.status
            or saved_password.value != password.value
        ):
            password.status = saved_password.status
            password.value = saved_password.value
            password.save()
            password_updated = True

        # Actualize resource
        if (
            password_updated
            or actual_resource.status != target_resource.status
            or actual_resource.full_hash != target_resource.full_hash
        ):
            target_resource.status = actual_resource.status
            target_resource.full_hash = actual_resource.full_hash
            target_resource.tracked_at = password.updated_at
            target_resource.update()

    def _actualize_outdated_passwords(self) -> None:
        """Actualize outdated passwords.

        It means some changes oscurred in the system and the passwords
        are outdated now. For instance, their status is incorrect.
        """
        resource_map = self._get_outdated_resources()

        if len(resource_map) == 0:
            return

        passwords = self._get_outdated_passwords(tuple(resource_map.keys()))

        for password in passwords:
            target, actual = resource_map[password.uuid]
            try:
                self._actualize_outdated_password(password, target, actual)
                LOG.debug("Password %s actualized", password.uuid)
            except Exception:
                LOG.exception("Error actualizing password %s", password.uuid)

    def _actualize_deleted_passwords(self) -> None:
        """Actualize passwords deleted by user."""
        deleted_passwords = self._get_deleted_passwords()

        if len(deleted_passwords) == 0:
            return

        for password in deleted_passwords:
            try:
                password.delete()
                LOG.debug("Outdated resource %s deleted", password.uuid)
            except Exception:
                LOG.exception("Error deleting resource %s", password.uuid)

    def _iteration(self) -> None:
        with contexts.Context().session_manager():
            try:
                self._actualize_new_passwords()
            except Exception:
                LOG.exception("Error actualizing new passwords")

            try:
                self._actualize_changed_passwords()
            except Exception:
                LOG.exception("Error actualizing changed passwords")

            try:
                self._actualize_outdated_passwords()
            except Exception:
                LOG.exception("Error actualizing outdated passwords")

            try:
                self._actualize_deleted_passwords()
            except Exception:
                LOG.exception("Error actualizing deleted passwords")
