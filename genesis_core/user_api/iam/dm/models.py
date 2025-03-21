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
from genesis_core.common import utils as u
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

    def change_secret_safe(self, old_secret, new_secret):
        self.validate_secret(old_secret)
        self.secret = new_secret


class ModelWithStatus(models.Model):

    STATUS = iam_c.Status

    status = properties.property(
        types.Enum([s.value for s in iam_c.Status]),
        default=STATUS.NEW.value,
    )


class ModelWithAlwaysActiveStatus(models.Model):

    STATUS = iam_c.AlwaysActiveStatus

    status = properties.property(
        types.Enum([s.value for s in iam_c.AlwaysActiveStatus]),
        default=STATUS.ACTIVE.value,
    )


class RolesInfo:

    def __init__(self, roles):
        super().__init__()
        self._roles = roles

    def get_response_body(self):
        return [role.get_storable_snapshot() for role in self._roles]


class User(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
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
    surname = properties.property(
        types.String(min_length=0, max_length=128),
        default="",
    )

    phone = properties.property(
        types.String(min_length=0, max_length=15),
        default=None,
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
    def me(cls, token_info=None):
        token_info = (
            token_info or contexts.get_context().iam_context.token_info
        )
        return User.objects.get_one(
            filters={"uuid": ra_filters.EQ(token_info.user_uuid)}
        )

    def make_newcomer(self):
        role_newcomer = Role.objects.get_one(
            filters={"uuid": ra_filters.EQ(c.NEWCOMER_ROLE_UUID)}
        )
        role_binding = RoleBinding(
            user=self,
            role=role_newcomer,
        )
        role_binding.save()
        return role_binding

    def get_my_roles(self):
        return RolesInfo(
            [
                role_binding.role
                for role_binding in RoleBinding.objects.get_all(
                    filters={"user": ra_filters.EQ(self)}
                )
            ]
        )

    def delete(self, session=None, **kwargs):
        u.remove_nested_dm(OrganizationMember, "user", self, session=session)
        u.remove_nested_dm(RoleBinding, "user", self, session=session)
        return super().delete(session=session, **kwargs)


class Role(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
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
    models.ModelWithRequiredNameDesc,
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
        Role,
        required=True,
    )

    permission = relationships.relationship(
        Permission,
        required=True,
    )


class Organization(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
    models.ModelWithTimestamp,
    ModelWithAlwaysActiveStatus,
    orm.SQLStorableWithJSONFieldsMixin,
):
    __tablename__ = "iam_organizations"
    __jsonfields__ = ["info"]

    info = properties.property(types.Dict(), default=dict)

    @classmethod
    def list_my(cls):
        user = User.me()

        member_bindings = OrganizationMember.objects.get_all(
            filters={
                "user": ra_filters.EQ(user),
            }
        )

        return [m.organization for m in member_bindings]

    @classmethod
    def get_default(cls, user=None):
        for member in OrganizationMember.objects.get_all(
            filters={
                "role": ra_filters.EQ(iam_c.OrganizationRole.OWNER.value),
                "user": ra_filters.EQ(user or User.me()),
            },
            limit=1,
            order_by={"created_at": "asc"},
        ):
            return member.organization
        return None

    def are_i_owner(self):
        user = User.me()
        for member in OrganizationMember.objects.get_all(
            filters={
                "organization": ra_filters.EQ(self),
                "user": ra_filters.EQ(user),
                "role": ra_filters.EQ(iam_c.OrganizationRole.OWNER.value),
            },
            limit=1,
        ):
            return True

        return False

    def are_i_member(self):
        user = User.me()
        for member in OrganizationMember.objects.get_all(
            filters={
                "organization": ra_filters.EQ(self),
                "user": ra_filters.EQ(user),
            },
            limit=1,
        ):
            return True

        return False


class OrganizationMember(
    models.ModelWithUUID,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "iam_organization_members"

    organization = relationships.relationship(
        Organization,
        prefetch=True,
        required=True,
    )
    user = relationships.relationship(
        User,
        prefetch=True,
        required=True,
    )
    role = properties.property(
        types.Enum([s.value for s in iam_c.OrganizationRole]),
        default=iam_c.OrganizationRole.MEMBER.value,
    )


class Project(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
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

    def add_owner(self, user):
        role_owner = Role.objects.get_one(
            filters={"uuid": ra_filters.EQ(c.OWNER_ROLE_UUID)}
        )
        role_binding = RoleBinding(
            user=user,
            role=role_owner,
            project=self,
        )
        role_binding.save()
        return role_binding

    @classmethod
    def get_default(cls, organization=None, user=None):
        user = user or User.me()
        org = organization or Organization.get_default(user=user)
        for role_binding in RoleBinding.objects.get_all(
            filters={
                "user": ra_filters.EQ(user),
            },
            order_by={"created_at": "asc"},
        ):
            if (
                role_binding.project
                and role_binding.project.organization == org
            ):
                return role_binding.project
        return None


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
    models.ModelWithRequiredNameDesc,
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

    @staticmethod
    def get_default_expiration_delta():
        return datetime.timedelta(minutes=60)

    @staticmethod
    def get_default_refresh_expiration_delta():
        return datetime.timedelta(days=1)

    expiration_delta = properties.property(
        types.TimeDelta(),
        default=get_default_expiration_delta,
    )
    refresh_expiration_delta = properties.property(
        types.TimeDelta(),
        default=get_default_refresh_expiration_delta,
    )

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
    expiration_at = properties.property(
        types.UTCDateTimeZ(),
        required=True,
    )
    refresh_expiration_at = properties.property(
        types.UTCDateTimeZ(),
        required=True,
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

    def __init__(self, user=None, scope="", project=None, **kwargs):
        user = user or User.me()
        now = datetime.datetime.now(datetime.timezone.utc)

        if "expiration_at" not in kwargs:
            expiration_delta = kwargs.get(
                "expiration_delta",
                self.get_default_expiration_delta(),
            )

            kwargs["expiration_at"] = now + expiration_delta

        if "refresh_expiration_at" not in kwargs:
            expiration_delta = kwargs.get(
                "refresh_expiration_delta",
                self.get_default_refresh_expiration_delta(),
            )

            kwargs["refresh_expiration_at"] = now + expiration_delta

        if project is None and scope:
            project = self._get_project_by_scope(user, scope)
        super().__init__(user=user, project=project, scope=scope, **kwargs)

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
        return now < self.refresh_expiration_at

    def validate_refresh_expiration(self):
        if not self.check_refresh_expiration():
            raise iam_e.InvalidRefreshTokenError()

    def check_expiration(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now < self.expiration_at

    def validate_expiration(self):
        if not self.check_refresh_expiration():
            raise iam_e.InvalidAuthTokenError()

    def _get_default_project(self, user):
        return Project.get_default(user=user)

    def _get_project_by_uuid(self, user, str_uuid):
        for project in Project.objects.get_all(
            filters={"uuid": ra_filters.EQ(str_uuid)},
            limit=1,
        ):
            return project

    def _get_project_by_scope(self, user, scope):
        scope = scope.lower()
        project = None
        for piece in scope.split(" "):
            if piece.startswith("project"):
                project_info = piece.split(":", 1)
                project = (
                    self._get_project_by_uuid(user, project_info[1])
                    if len(project_info) > 1 and project_info[1] != "default"
                    else self._get_default_project(user)
                )
                break

        return project

    def refresh(self, scope=None):
        scope = scope or self.scope
        now = datetime.datetime.now(datetime.timezone.utc)
        new_expiration_at = now + self.expiration_delta
        self.expiration_at = new_expiration_at
        self.project = self._get_project_by_scope(self.user, scope)
        self.scope = scope
        self.update()

    def get_response_body(self):
        ctx = contexts.get_context()
        storage = ctx.context_storage

        now = datetime.datetime.now(datetime.timezone.utc)
        algorithm = storage.get(
            iam_c.STORAGE_KEY_IAM_TOKEN_ENCRYPTION_ALGORITHM
        )

        access_token_info = {
            "exp": int(self.expiration_at.timestamp()),
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
            "exp": int(self.expiration_at.timestamp()),
            "iat": int(self.created_at.timestamp()),
            "auth_time": int(self.created_at.timestamp()),
            "jti": str(self.uuid),
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(self.user.uuid),
            "email": self.user.email,
            "name": f" {self.user.first_name} {self.user.last_name}",
            "project_id": str(self.project.uuid) if self.project else None,
        }

        id_token = algorithm.encode(id_token_info)

        refresh_token_info = {
            "exp": int(self.refresh_expiration_at.timestamp()),
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
            "expires_at": int(self.expiration_at.timestamp()),
            "expires_in": (self.expiration_at - now).seconds,
            "id_token": id_token,
            "refresh_token": refresh_token,
            "refresh_expires_in": (self.refresh_expiration_at - now).seconds,
            "scope": self.scope,
        }

    @classmethod
    def my(cls, token_info=None):
        token_info = (
            token_info or contexts.get_context().iam_context.token_info
        )
        for token in Token.objects.get_all(
            filters={"uuid": ra_filters.EQ(token_info.uuid)},
            limit=1,
        ):
            return token
        raise iam_e.InvalidAuthTokenError()

    def introspect(self, token_info=None):
        user = User.me(token_info=token_info)

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


class MeInfo:

    def __init__(self):
        super().__init__()
        self._user = self.get_user()

    def get_user(self):
        return User.me()

    def get_response_body(self):
        user = self._user.get_storable_snapshot()
        for drop_field in ["otp_secret", "salt", "secret_hash", "secret"]:
            user.pop(drop_field, None)

        organizations = []
        for organization in Organization.list_my():
            organizations.append(organization.get_storable_snapshot())

        project = Token.my().project
        project_id = str(project.uuid) if project else None

        return {
            "user": user,
            "organization": organizations,
            "project_id": project_id,
        }


class IamClient(
    models.ModelWithUUID,
    models.ModelWithRequiredNameDesc,
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

    def get_token_by_password(
        self,
        username,
        password,
        scope=iam_c.PARAM_SCOPE_DEFAULT,
        ttl=None,
        refresh_ttl=None,
        root_endpoint=(
            f"http://{c.DEFAULT_USER_API_HOST}:{c.DEFAULT_USER_API_PORT}/v1/"
        ),
        **kwargs,
    ):
        expiration_delta = (
            datetime.timedelta(seconds=float(ttl))
            if ttl is not None
            else Token.get_default_expiration_delta()
        )
        refresh_expiration_delta = (
            datetime.timedelta(seconds=float(refresh_ttl))
            if refresh_ttl is not None
            else Token.get_default_refresh_expiration_delta()
        )
        for user in User.objects.get_all(
            filters={"name": ra_filters.EQ(username)}
        ):
            user.validate_secret(secret=password)
            token = Token(
                user=user,
                scope=scope,
                issuer=f"{root_endpoint}iam/clients/{self.uuid}",
                audience=self.client_id,
                expiration_delta=expiration_delta,
                refresh_expiration_delta=refresh_expiration_delta,
                **kwargs,
            )
            token.insert()
            return token
        else:
            raise iam_exceptions.UserNotFound(username=username)

    def get_token_by_refresh_token(self, refresh_token, scope=None):
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
            token.refresh(scope=scope)
            return token
        else:
            raise iam_e.InvalidRefreshTokenError()

    def introspect(self):
        return Token.my().introspect()

    def me(self):
        return MeInfo()
