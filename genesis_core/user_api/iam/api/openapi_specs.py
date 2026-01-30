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

from restalchemy.openapi import constants as oa_c
from genesis_core.user_api.iam import constants as c

responses = {}
responses.update(
    oa_c.build_openapi_user_response(
        **{
            "type": "object",
            "required": [
                "access_token",
                "expires_at",
                "id_token",
                "refresh_token",
                "scope",
                "token_type",
            ],
            "properties": {
                "access_token": {
                    "type": "string",
                    "description": "JWT access token",
                    "example": "eyJhbGciOiJSUzI...",
                },
                "expires_at": {
                    "type": "integer",
                    "format": "int64",
                    "description": "UNIX timestamp when token expires",
                    "example": 1740524674,
                },
                "id_token": {
                    "type": "string",
                    "description": "OpenID Connect ID Token",
                    "example": "eyJhbGciOiJSUzI1NiIsInR...",
                },
                "refresh_token": {
                    "type": "string",
                    "description": "Refresh token",
                    "example": "eyJhbGciOiJIUzUxMiIsIn...",
                },
                "scope": {
                    "type": "string",
                    "description": "Granted scopes (space-separated)",
                    "example": "openid email profile",
                },
                "token_type": {
                    "type": "string",
                    "description": "Type of token",
                    "enum": ["Bearer"],
                    "example": "Bearer",
                },
            },
        }
    )
)
responses.update(
    oa_c.build_openapi_user_response(
        code=401,
        **{
            "title": "Wrong OTP error",
            "description": "The provided otp code is invalid",
            "type": "object",
            "required": [
                "error",
                "error_description",
            ],
            "properties": {
                "error": {
                    "type": "string",
                    "description": "Error class name",
                    "example": "OSError",
                },
                "error_description": {
                    "type": "string",
                    "description": "Error description",
                    "example": "A human-readable explanation of problem",
                },
            },
            "example": {
                "error": "invalid_client",
                "error_description": "The provided otp code is invalid",
            },
        },
    )
)


OA_SPEC_GET_TOKEN_KWARGS = dict(
    summary="Create token by password",
    parameters=[
        oa_c.build_openapi_parameter(
            name="IamClientUuid",
            openapi_type="string",
            param_type="path",
            required=True,
        ),
        oa_c.build_openapi_parameter(
            name="X-OTP",
            openapi_type="string",
            param_type="header",
            required=False,
        ),
    ],
    responses=responses,
    request_body=oa_c.build_openapi_req_body(
        description="",
        content_type="application/x-www-form-urlencoded",
        schema={
            "oneOf": [
                {
                    "type": "object",
                    "required": [
                        "grant_type",
                        "client_id",
                        "client_secret",
                        "username",
                        "password",
                    ],
                    "properties": {
                        "grant_type": {
                            "type": "string",
                            "enum": [c.GRANT_TYPE_PASSWORD],
                        },
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "scope": {"type": "string"},
                        "ttl": {"type": "number", "format": "float"},
                        "refresh_ttl": {"type": "string", "format": "float"},
                    },
                },
                {
                    "type": "object",
                    "required": [
                        "grant_type",
                        "client_id",
                        "client_secret",
                        "email",
                        "password",
                    ],
                    "properties": {
                        "grant_type": {
                            "type": "string",
                            "enum": [c.GRANT_TYPE_PASSWORD_EMAIL],
                        },
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "scope": {"type": "string"},
                        "ttl": {"type": "number", "format": "float"},
                        "refresh_ttl": {"type": "string", "format": "float"},
                    },
                },
                {
                    "type": "object",
                    "required": [
                        "grant_type",
                        "client_id",
                        "client_secret",
                        "login",
                        "password",
                    ],
                    "properties": {
                        "grant_type": {
                            "type": "string",
                            "enum": [c.GRANT_TYPE_PASSWORD_LOGIN],
                        },
                        "client_id": {"type": "string"},
                        "client_secret": {"type": "string"},
                        "login": {"type": "string"},
                        "password": {"type": "string"},
                        "scope": {"type": "string"},
                        "ttl": {"type": "number", "format": "float"},
                        "refresh_ttl": {"type": "string", "format": "float"},
                    },
                },
                {
                    "type": "object",
                    "required": [
                        "grant_type",
                        "refresh_token",
                    ],
                    "properties": {
                        "grant_type": {
                            "type": "string",
                            "enum": ["refresh_token"],
                        },
                        "refresh_token": {"type": "string"},
                    },
                },
            ],
            "discriminator": {"propertyName": "grant_type"},
        },
    ),
)
