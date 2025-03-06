# Copyright 2025 Genesis Corporation
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

import base64
import datetime
import hashlib
import secrets
import uuid as sys_uuid

from gcl_iam import exceptions as iam_e
from gcl_iam import tokens
import jinja2
from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.common import contexts
from restalchemy.dm import filters as ra_filters
from restalchemy.storage.sql import orm


from genesis_core.common import constants as c
from genesis_core.user_api.iam import constants as iam_c
from genesis_core.user_api.iam import exceptions as iam_exceptions


class ModelWithSecret(models.Model, models.CustomPropertiesMixin):

    __custom_properties__ = {
        "secret": types.String(min_length=5, max_length=128),
    }

    salt = properties.property(
        types.String(min_length=24, max_length=24),
        required=False,
    )

    secret_hash = properties.property(
        types.String(min_length=128, max_length=128),
        required=True,
    )

    def __init__(self, secret, salt=None, **kwargs):
        salt = salt or self._generate_salt()
        super().__init__(
            secret_hash=self._generate_hash(
                secret=secret,
                secret_salt=salt,
                global_salt=self._global_salt,
            ),
            salt=salt,
            **kwargs,
        )

    def _generate_salt(self, length=18):
        return base64.b64encode(secrets.token_bytes(length)).decode("utf-8")

    @property
    def _global_salt(self):
        ctx = contexts.get_context()
        storage = ctx.context_storage
        return storage.get(iam_c.STORAGE_KEY_IAM_GLOBAL_SALT)

    @classmethod
    def _generate_hash(cls, secret, secret_salt, global_salt):

        raw_secret_salt = base64.b64decode(secret_salt)
        raw_global_salt = base64.b64decode(global_salt)

        hashed = hashlib.pbkdf2_hmac(
            "sha512",
            secret.encode("utf-8"),
            raw_secret_salt + raw_global_salt,
            251685,  # count of iterations
        )

        return hashed.hex()

    def check_secret(self, secret):
        return self.secret_hash == self._generate_hash(
            secret=secret,
            secret_salt=self.salt,
            global_salt=self._global_salt,
        )

    def validate_secret(self, secret):
        if not self.check_secret(secret):
            raise iam_e.CredentialsAreInvalidError()

    @property
    def secret(self):
        return "*******"

    @secret.setter
    def secret(self, value):
        self.salt = self._generate_salt()
        self.secret_hash = self._generate_hash(
            secret=value,
            secret_salt=self.salt,
            global_salt=self._global_salt,
        )


class ModelWithStatus(models.Model):

    STATUS = iam_c.Status

    status = properties.property(
        types.Enum([s for s in iam_c.Status]),
        default=STATUS.NEW,
    )


class ModelWithAlwaysActiveStatus(models.Model):

    STATUS = iam_c.AlwaysActiveStatus

    status = properties.property(
        types.Enum([s for s in iam_c.AlwaysActiveStatus]),
        default=STATUS.ACTIVE,
    )


class User(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithSecret,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_users"

    first_name = properties.property(
        types.String(min_length=1, max_length=128),
        required=True,
    )

    last_name = properties.property(
        types.String(min_length=1, max_length=128),
        required=True,
    )

    email = properties.property(
        types.Email(max_length=128),
        required=True,
    )

    otp_secret = properties.property(
        types.String(max_length=128),
        default="",
    )

    otp_enabled = properties.property(
        types.Boolean(),
        default=False,
    )

    def get_response_body(self):
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
        }

    @classmethod
    def my(cls, token_info=None):
        token_info = (
            token_info or contexts.get_context().iam_context.token_info
        )
        return User.objects.get_one(
            filters={"uuid": ra_filters.EQ(token_info.user_uuid)}
        )


class Role(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_roles"

    project_id = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
        read_only=True,
    )


class Permission(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_permissions"


class PermissionBinding(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_binding_permissions"

    project_id = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
        read_only=True,
    )
    role = relationships.relationship(
        "Role",
        required=True,
    )

    permission = relationships.relationship(
        "Permission",
        required=True,
    )


class Organization(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_organizations"


class Project(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_projects"

    organization = relationships.relationship(
        Organization,
        required=True,
        prefetch=True,
    )


class PermissionFastView(
    models.ModelWithUUID,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_permissions_fast_view"

    permission = relationships.relationship(
        Permission,
        prefetch=True,
        required=True,
    )
    user = relationships.relationship(
        User,
        prefetch=True,
        required=True,
    )
    role = relationships.relationship(
        Role,
        prefetch=True,
        required=True,
    )
    project = relationships.relationship(
        Project,
        prefetch=True,
        required=False,
    )


class RoleBinding(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_binding_roles"

    project = relationships.relationship(
        Project,
        default=None,
    )
    user = relationships.relationship(
        User,
        required=True,
    )
    role = relationships.relationship(
        Role,
        prefetch=True,
        required=True,
    )


class Idp(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithSecret,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_idp"

    project_id = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
        read_only=True,
    )
    client_id = properties.property(
        types.String(max_length=64),
        required=True,
    )
    scope = properties.property(
        types.String(max_length=64),
        default="openid",
    )
    well_known_endpoint = properties.property(
        types.String(max_length=256),
        required=True,
    )

    redirect_uri_template = properties.property(
        types.String(max_length=256),
        default=(
            "{{ host_url }}/v1/iam/idp/"
            "{{ idp_uuid }}/actions/callback/invoke"
        ),
    )

    def get_redirect_uri(self, request_params):
        return jinja2.Template(self.redirect_uri_template).render(
            **request_params
        )


class Introspection(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
):

    user = relationships.relationship(
        User,
        required=True,
    )
    project = relationships.relationship(
        Project,
        required=False,
    )
    otp_verified = properties.property(
        types.Boolean(),
        default=False,
    )
    permissions = properties.property(
        types.List(),
        default=list,
    )

    def get_response_body(self):
        return {
            "user_info": self.user.get_response_body(),
            "project_id": str(self.project.uuid) if self.project else None,
            "otp_verified": self.otp_verified,
            "permissions": [
                permission.name for permission in self.permissions
            ],
        }


class Token(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_tokens"

    experation_delta = datetime.timedelta(minutes=15)
    refresh_experation_delta = datetime.timedelta(days=1)

    user = relationships.relationship(
        User,
        prefetch=True,
        required=True,
    )
    project = relationships.relationship(
        Project,
        prefetch=True,
        required=False,
    )
    experation_at = properties.property(
        types.UTCDateTimeZ(),
        default=lambda: (
            datetime.datetime.now(datetime.timezone.utc)
            + Token.experation_delta
        ),
    )
    refresh_experation_at = properties.property(
        types.UTCDateTimeZ(),
        default=lambda: (
            datetime.datetime.now(datetime.timezone.utc)
            + Token.refresh_experation_delta
        ),
    )
    refresh_token_uuid = properties.property(
        types.UUID(),
        default=sys_uuid.uuid4,
    )
    issuer = properties.property(
        types.String(max_length=256),
        required=False,
    )
    audience = properties.property(
        types.String(max_length=64),
        default="account",
    )
    typ = properties.property(
        types.String(max_length=64),
        default="Bearer",
    )
    scope = properties.property(
        types.String(max_length=128),
        default=iam_c.PARAM_SCOPE_DEFAULT,
    )

    def _get_key_by_encryption_algorithm(self, algorithm):
        ctx = contexts.get_context()
        storage = ctx.context_storage
        if algorithm == iam_c.ALGORITHM_HS256:
            return {
                "key": storage.get(
                    iam_c.STORAGE_KEY_IAM_TOKEN_HS256_ENCRYPTION_KEY
                )
            }
        raise iam_e.IncorrectEncriptionAlgorithmError(algorithm=algorithm)

    def check_refresh_expiration(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now < self.refresh_experation_at

    def validate_refresh_expiration(self):
        if not self.check_refresh_expiration():
            raise iam_e.InvalidRefreshTokenError()

    def check_expiration(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now < self.experation_at

    def validate_expiration(self):
        if not self.check_refresh_expiration():
            raise iam_e.InvalidAuthTokenError()

    def refresh(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        new_experation_at = now + Token.experation_delta
        self.experation_at = new_experation_at
        self.update()

    def get_response_body(self):
        ctx = contexts.get_context()
        storage = ctx.context_storage

        now = datetime.datetime.now(datetime.timezone.utc)
        algorithm = storage.get(
            iam_c.STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM
        )

        access_token_info = {
            "exp": int(self.experation_at.timestamp()),
            "iat": int(self.created_at.timestamp()),
            "auth_time": int(self.created_at.timestamp()),
            "jti": str(self.uuid),
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(self.user.uuid),
            "typ": self.typ,
        }
        access_token = algorithm.encode(access_token_info)

        id_token_info = {
            "exp": int(self.experation_at.timestamp()),
            "iat": int(self.created_at.timestamp()),
            "auth_time": int(self.created_at.timestamp()),
            "jti": str(self.uuid),
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(self.user.uuid),
            "email": self.user.email,
            "name": f" {self.user.first_name} {self.user.last_name}",
        }

        id_token = algorithm.encode(id_token_info)

        refresh_token_info = {
            "exp": int(self.refresh_experation_at.timestamp()),
            "iat": int(self.created_at.timestamp()),
            "jti": str(self.refresh_token_uuid),
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(self.user.uuid),
        }

        refresh_token = algorithm.encode(refresh_token_info)

        return {
            "access_token": access_token,
            "token_type": self.typ,
            "expires_at": int(self.experation_at.timestamp()),
            "expires_in": (self.experation_at - now).seconds,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "refresh_expires_in": (self.refresh_experation_at - now).seconds,
            "scope": self.scope,
        }

    @classmethod
    def my(cls, token_info=None):
        token_info = (
            token_info or contexts.get_context().iam_context.token_info
        )
        for token in Token.objects.get_all(
            filters={"uuid": ra_filters.EQ(token_info.uuid)}
        ):
            return token
        raise iam_e.InvalidAuthTokenError()

    def introspect(self, token_info=None):
        user = User.my(token_info=token_info)

        values = PermissionFastView.objects.get_all(
            filters={
                "user": ra_filters.EQ(user),
                "project": ra_filters.Is(self.project),
            }
        )

        return Introspection(
            user=self.user,
            project=self.project,
            permissions=[v.permission for v in values],
        )


class IamClient(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    ModelWithSecret,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_clients"

    project_id = properties.property(
        types.AllowNone(types.UUID()),
        default=None,
        read_only=True,
    )
    client_id = properties.property(
        types.String(max_length=64),
        required=True,
    )
    redirect_url = properties.property(
        types.Url(),
        required=True,
    )

    def validate_client_creds(self, client_id, client_secret):
        if not (
            self.client_id == client_id or self.check_secret(client_secret)
        ):
            raise iam_e.CredentialsAreInvalidError()

    def _get_project_by_scope(self, scope):
        return None

    def get_token_by_password(
        self,
        username,
        password,
        scope=iam_c.PARAM_SCOPE_DEFAULT,
        root_endpoint=(
            f"http://{c.DEFAULT_USER_API_HOST}:{c.DEFAULT_USER_API_PORT}"
        ),
        **kwargs,
    ):
        for user in User.objects.get_all(
            filters={"name": ra_filters.EQ(username)}
        ):
            user.validate_secret(secret=password)
            token = Token(
                user=user,
                project=self._get_project_by_scope(scope),
                scope=scope,
                issuer=f"{root_endpoint}/v1/iam/clients/{self.uuid}",
                audience=self.client_id,
                **kwargs,
            )
            token.insert()
            return token
        else:
            raise iam_exceptions.UserNotFound(username=username)

    def get_token_by_refresh_token(self, refresh_token):
        context = contexts.get_context()
        storage = context.context_storage
        algorithm = storage.get(
            iam_c.STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM
        )
        refresh_token_info = tokens.RefreshToken(
            token=refresh_token,
            algorithm=algorithm,
            ignore_audience=True,
            ignore_expiration=True,
        )
        for token in Token.objects.get_all(
            filters={
                "refresh_token_uuid": ra_filters.EQ(refresh_token_info.uuid)
            }
        ):
            token.validate_refresh_expiration()
            token.refresh()
            return token
        else:
            raise iam_e.InvalidRefreshTokenError()

    def introspect(self):
        return Token.my().introspect()
