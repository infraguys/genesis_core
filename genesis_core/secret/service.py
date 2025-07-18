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

    def _get_new_certificates(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[models.Certificate]:
        return models.Certificate.get_new_certificates(limit=limit)

    def _get_changed_certificates(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[models.Certificate]:
        return models.Certificate.get_updated_certificates(limit=limit)

    def _get_deleted_certificates(
        self,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> list[ua_models.TargetResource]:
        return models.Certificate.get_deleted_certificates(limit=limit)

    def _get_outdated_resources(
        self,
        kind: str,
        limit: int = sc.DEFAULT_SQL_LIMIT,
    ) -> dict[
        sys_uuid.UUID,  # Resource UUID
        tuple[ua_models.TargetResource, ua_models.Resource],
    ]:
        outdated = ua_models.OutdatedResource.objects.get_all(
            filters={"kind": dm_filters.EQ(kind)},
            limit=limit,
        )
        return {
            pair.target_resource.uuid: (
                pair.target_resource,
                pair.actual_resource,
            )
            for pair in outdated
        }

    def _get_outdated_secrets(
        self,
        model: models.Secret,
        uuids: tp.Collection[sys_uuid.UUID],
    ) -> list[models.Secret]:
        return model.objects.get_all(
            filters={"uuid": dm_filters.In(str(p) for p in uuids)},
        )

    def _actualize_new_secrets(
        self, kind: str, secrets: tp.Collection[models.Secret]
    ) -> None:
        """Actualize new secrets."""
        # Just create resources for new secrets
        for secret in secrets:
            secret_resource = secret.to_ua_resource(kind)
            try:
                secret_resource.insert()
                secret.status = sc.SecretStatus.IN_PROGRESS.value
                secret.save()

                # Commit tracked_at ts
                secret_resource.tracked_at = secret.updated_at
                secret_resource.status = secret.status

                secret_resource.update()
                LOG.info(
                    "Certificate resource %s created", secret_resource.uuid
                )
            except Exception:
                LOG.exception("Error creating cert resource %s", secret.uuid)

    def _actualize_changed_secrets(
        self, kind: str, changed_secrets: dict[sys_uuid.UUID, models.Secret]
    ) -> None:
        """Actualize secrets changed by user."""
        if len(changed_secrets) == 0:
            return

        secret_resources = ua_models.TargetResource.objects.get_all(
            filters={
                "uuid": dm_filters.In(str(p) for p in changed_secrets.keys()),
                "kind": dm_filters.EQ(kind),
            }
        )

        # Update every resource in accordance with the new secret
        for resource in secret_resources:
            secret = changed_secrets[resource.uuid]
            new_resource = secret.to_ua_resource(kind)

            # Update the original resource
            resource.update_value(new_resource)
            try:
                secret.status = sc.SecretStatus.IN_PROGRESS.value
                secret.save()

                # Commit the tracked_at timestamp
                resource.tracked_at = secret.updated_at
                resource.status = secret.status
                resource.update()
                LOG.debug(
                    "Secret(%s) resource %s updated", kind, resource.uuid
                )
            except Exception:
                LOG.exception(
                    "Error updating secret(%s) resource %s",
                    kind,
                    resource.uuid,
                )

    def _actualize_outdated_secrets(
        self,
        kind: str,
        model: models.Secret,
        secret_handler: tp.Callable[
            [models.Secret, ua_models.TargetResource, ua_models.Resource], None
        ],
    ) -> None:
        """Actualize outdated secrets.

        It means some changes occurred in the system and the secrets
        are outdated now. For instance, their status is incorrect.
        """
        resource_map = self._get_outdated_resources(kind)

        if len(resource_map) == 0:
            return

        secrets = self._get_outdated_secrets(model, tuple(resource_map.keys()))

        for secret in secrets:
            target, actual = resource_map[secret.uuid]
            try:
                secret_handler(secret, target, actual)
                LOG.debug("Secret(%s) %s actualized", kind, secret.uuid)
            except Exception:
                LOG.exception(
                    "Error actualizing secret(%s) %s", kind, secret.uuid
                )

    def _actualize_deleted_secrets(
        self, secrets: tp.Collection[ua_models.TargetResource]
    ) -> None:
        """Actualize secrets deleted by user."""
        for secret in secrets:
            try:
                secret.delete()
                LOG.debug(
                    "Outdated resource(%s) %s deleted",
                    secret.kind,
                    secret.uuid,
                )
            except Exception:
                LOG.exception(
                    "Error deleting resource(%s) %s", secret.kind, secret.uuid
                )

    # Passwords

    def _actualize_new_passwords(self) -> None:
        """Actualize new passwords."""
        passwords = self._get_new_passwords()
        self._actualize_new_secrets(sc.PASSWORD_KIND, passwords)

    def _actualize_changed_passwords(self) -> None:
        """Actualize passwords changed by user."""
        changed_passwords = {p.uuid: p for p in self._get_changed_passwords()}
        self._actualize_changed_secrets(sc.PASSWORD_KIND, changed_passwords)

    def _actualize_outdated_password(
        self,
        password: models.Password,
        target_resource: ua_models.TargetResource,
        actual_resource: ua_models.Resource,
    ) -> None:
        """Actualize outdated password."""
        password_updated = False
        status_updated = False
        actual_pass = models.Password.from_ua_resource(actual_resource)

        # `ACTIVE` only if the hash is the same
        if (
            actual_resource.status == sc.SecretStatus.ACTIVE
            and target_resource.hash == actual_resource.hash
        ):
            status_updated = True
        elif (
            actual_resource.status != sc.SecretStatus.ACTIVE
            and target_resource.status != actual_resource.status
        ):
            status_updated = True

        # Actualize password
        if status_updated or actual_pass.value != password.value:
            if status_updated:
                password.status = actual_pass.status
            password.value = actual_pass.value
            password.save()
            password_updated = True

        # Actualize resource
        if (
            password_updated
            or actual_resource.full_hash != target_resource.full_hash
        ):
            if status_updated:
                target_resource.status = actual_resource.status
            target_resource.full_hash = actual_resource.full_hash
            target_resource.tracked_at = password.updated_at
            target_resource.update()

    def _actualize_outdated_passwords(self) -> None:
        """Actualize outdated passwords.

        It means some changes occurred in the system and the passwords
        are outdated now. For instance, their status is incorrect.
        """
        self._actualize_outdated_secrets(
            sc.PASSWORD_KIND,
            models.Password,
            self._actualize_outdated_password,
        )

    def _actualize_deleted_passwords(self) -> None:
        """Actualize passwords deleted by user."""
        deleted_passwords = self._get_deleted_passwords()
        self._actualize_deleted_secrets(deleted_passwords)

    # Certificates

    def _actualize_new_certificates(self) -> None:
        """Actualize new certificates."""
        certs = self._get_new_certificates()
        self._actualize_new_secrets(sc.CERTIFICATE_KIND, certs)

    def _actualize_changed_certificates(self) -> None:
        """Actualize certificates changed by user."""
        changed_certs = {
            crt.uuid: crt for crt in self._get_changed_certificates()
        }
        self._actualize_changed_secrets(sc.CERTIFICATE_KIND, changed_certs)

    def _actualize_outdated_certificate(
        self,
        certificate: models.Certificate,
        target_resource: ua_models.TargetResource,
        actual_resource: ua_models.Resource,
    ) -> None:
        """Actualize outdated certificate."""
        certificate_updated = False
        status_updated = False
        actual_cert = models.Certificate.from_ua_resource(actual_resource)

        # `ACTIVE` only if the hash is the same
        if (
            actual_resource.status == sc.SecretStatus.ACTIVE
            and target_resource.hash == actual_resource.hash
        ):
            status_updated = True
        elif (
            actual_resource.status != sc.SecretStatus.ACTIVE
            and target_resource.status != actual_resource.status
        ):
            status_updated = True

        # Actualize certificate
        if (
            status_updated
            or actual_cert.key != certificate.key
            or actual_cert.cert != certificate.cert
            or actual_cert.expiration_at != certificate.expiration_at
        ):
            if status_updated:
                certificate.status = actual_cert.status
            certificate.key = actual_cert.key
            certificate.cert = actual_cert.cert
            certificate.expiration_at = actual_cert.expiration_at
            certificate.save()
            certificate_updated = True

        # Actualize resource
        if (
            certificate_updated
            or actual_resource.full_hash != target_resource.full_hash
        ):
            if status_updated:
                target_resource.status = actual_resource.status
            target_resource.full_hash = actual_resource.full_hash
            target_resource.tracked_at = certificate.updated_at
            target_resource.update()

    def _actualize_outdated_certificates(self) -> None:
        """Actualize outdated certificates.

        It means some changes occurred in the system and the certificates
        are outdated now. For instance, their status is incorrect.
        """
        self._actualize_outdated_secrets(
            sc.CERTIFICATE_KIND,
            models.Certificate,
            self._actualize_outdated_certificate,
        )

    def _actualize_deleted_certificates(self) -> None:
        """Actualize certificates deleted by user."""
        deleted_certificates = self._get_deleted_certificates()
        self._actualize_deleted_secrets(deleted_certificates)

    def _actualize_passwords(self) -> None:
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

    def _actualize_certificates(self) -> None:
        try:
            self._actualize_new_certificates()
        except Exception:
            LOG.exception("Error actualizing new certificates")

        try:
            self._actualize_changed_certificates()
        except Exception:
            LOG.exception("Error actualizing changed certificates")

        try:
            self._actualize_outdated_certificates()
        except Exception:
            LOG.exception("Error actualizing outdated certificates")

        try:
            self._actualize_deleted_certificates()
        except Exception:
            LOG.exception("Error actualizing deleted certificates")

    def _iteration(self) -> None:
        with contexts.Context().session_manager():
            self._actualize_passwords()
            self._actualize_certificates()
