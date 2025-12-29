#!/usr/bin/env python3

# Copyright 2025 Genesis Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import logging
import secrets
import string
import sys
import urllib.parse

import requests


class UserAlreadyExistsError(Exception):
    """Raised when a user already exists in IAM."""


def _build_base_url(url: str) -> str:
    return url.rstrip("/")


def _normalize_auth_header(token: str) -> str:
    token = token.strip()
    if not token:
        raise ValueError("--token must not be empty")

    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def _generate_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _strip_or_none(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    return value


def _request_timeout(timeout: float) -> float:
    if timeout <= 0:
        raise ValueError("--timeout must be positive")
    return timeout


def _iam_user_url(iam_base_url: str, user_uuid: str) -> str:
    base = _build_base_url(iam_base_url)
    return urllib.parse.urljoin(f"{base}/", f"v1/iam/users/{user_uuid}")


def _iam_users_collection_url(iam_base_url: str) -> str:
    base = _build_base_url(iam_base_url)
    return urllib.parse.urljoin(f"{base}/", "v1/iam/users/")


def _get_existing_user(
    session: requests.Session,
    iam_base_url: str,
    auth_header_value: str,
    user_uuid: str,
    timeout: float,
) -> dict | None:
    url = _iam_user_url(iam_base_url=iam_base_url, user_uuid=user_uuid)
    headers = {"Authorization": auth_header_value}
    response = session.get(url, headers=headers, timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise RuntimeError(
            "Failed to check user existence in IAM. "
            f"uuid={user_uuid} status={response.status_code} body={response.text}"
        )
    payload = response.json()
    if isinstance(payload, dict):
        return payload
    return {"raw": payload}


def _build_user_payload(
    user: dict,
    description: str,
    keycloak_endpoint: str,
    keycloak_realm: str,
    keycloak_client_id: str,
    keycloak_client_secret: str,
    password_length: int,
    include_uuid: bool,
) -> dict:
    email = _strip_or_none(user.get("email"))
    username = _strip_or_none(user.get("username"))
    first_name = _strip_or_none(user.get("firstname"))
    last_name = _strip_or_none(user.get("lastname"))

    payload: dict = {
        "username": username or email or "",
        "description": description,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": _generate_password(password_length),
        "user_source": {
            "kind": "KEYCLOAK",
            "endpoint": keycloak_endpoint,
            "realm": keycloak_realm,
            "client_id": keycloak_client_id,
            "client_secret": keycloak_client_secret,
        },
    }

    surname = _strip_or_none(user.get("surname"))
    if surname is not None:
        payload["surname"] = surname

    if include_uuid and user.get("uuid"):
        payload["uuid"] = user.get("uuid")

    return payload


def _create_user(
    session: requests.Session,
    iam_base_url: str,
    auth_header_value: str,
    payload: dict,
    timeout: float,
) -> dict:
    url = _iam_users_collection_url(iam_base_url=iam_base_url)
    headers = {
        "Authorization": auth_header_value,
        "Content-Type": "application/json",
    }
    response = session.post(
        url, headers=headers, json=payload, timeout=timeout
    )

    if response.status_code in {200, 201}:
        return response.json()

    if response.status_code == 409:
        raise UserAlreadyExistsError()

    raise RuntimeError(
        "Failed to create user in IAM. "
        f"status={response.status_code} body={response.text}"
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import users from JSON into IAM with KEYCLOAK user_source.",
        epilog=(
            "Example:\n"
            "  import_keycloak_users_to_iam.py --iam-url http://127.0.0.1:11010 "
            "--token <token> --users users.json --keycloak-endpoint https://kc.example.com "
            "--keycloak-realm master --keycloak-client-id UserTransfer --keycloak-client-secret <secret>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--iam-url",
        required=True,
        help="IAM base URL, e.g. http://127.0.0.1:11010",
    )
    parser.add_argument(
        "--token",
        required=True,
        help="IAM authorization token (either raw token or full 'Bearer ...' value)",
    )
    parser.add_argument(
        "--users",
        required=True,
        help="Path to JSON file produced by fetch_keycloak_users.py",
    )

    parser.add_argument(
        "--keycloak-endpoint",
        required=True,
        help="Keycloak base URL used in IAM user_source",
    )
    parser.add_argument(
        "--keycloak-realm",
        required=True,
        help="Keycloak realm used in IAM user_source",
    )
    parser.add_argument(
        "--keycloak-client-id",
        required=True,
        help="Keycloak client_id used in IAM user_source",
    )
    parser.add_argument(
        "--keycloak-client-secret",
        required=True,
        help="Keycloak client_secret used in IAM user_source",
    )

    parser.add_argument(
        "--description",
        default="User From Keycloak",
        help="Description to set for created users (default: 'User From Keycloak')",
    )
    parser.add_argument(
        "--password-length",
        type=int,
        default=32,
        help="Generated password length (default: 32)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout seconds (default: 30)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification",
    )
    parser.add_argument(
        "--ignore-uuid",
        action="store_true",
        help="Do not include uuid in create payload",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    timeout = _request_timeout(args.timeout)
    if args.password_length < 5:
        raise ValueError("--password-length must be at least 5")

    auth_header_value = _normalize_auth_header(args.token)

    session = requests.Session()
    session.verify = not args.insecure

    with open(args.users, "r", encoding="utf-8") as f:
        users = json.load(f)

    if not isinstance(users, list):
        raise ValueError("Input JSON must contain a list of users")

    created = 0
    skipped = 0
    failed = 0

    for user in users:
        if not isinstance(user, dict):
            continue

        user_uuid = user.get("uuid")
        username = _strip_or_none(user.get("username"))
        email = _strip_or_none(user.get("email"))
        log_username = username or email or ""

        if not user_uuid:
            logging.warning(
                "Skipping user without uuid. username=%s", log_username
            )
            skipped += 1
            continue

        try:
            existing = _get_existing_user(
                session=session,
                iam_base_url=args.iam_url,
                auth_header_value=auth_header_value,
                user_uuid=user_uuid,
                timeout=timeout,
            )
        except requests.RequestException as e:
            logging.error(
                "Network error while checking user existence. username=%s uuid=%s error=%s",
                log_username,
                user_uuid,
                e,
            )
            failed += 1
            continue
        except Exception as e:
            logging.error(
                "Failed to check user existence. username=%s uuid=%s error=%s",
                log_username,
                user_uuid,
                e,
            )
            failed += 1
            continue

        if existing is not None:
            skipped += 1
            continue

        payload = _build_user_payload(
            user=user,
            description=args.description,
            keycloak_endpoint=args.keycloak_endpoint,
            keycloak_realm=args.keycloak_realm,
            keycloak_client_id=args.keycloak_client_id,
            keycloak_client_secret=args.keycloak_client_secret,
            password_length=args.password_length,
            include_uuid=not args.ignore_uuid,
        )

        logging.info(
            "Creating user. username=%s uuid=%s", log_username, user_uuid
        )
        try:
            _create_user(
                session=session,
                iam_base_url=args.iam_url,
                auth_header_value=auth_header_value,
                payload=payload,
                timeout=timeout,
            )
            created += 1
        except UserAlreadyExistsError:
            logging.info(
                "User already exists, skipping. username=%s uuid=%s",
                log_username,
                user_uuid,
            )
            skipped += 1
            continue
        except requests.RequestException as e:
            logging.error(
                "Network error while creating user. username=%s uuid=%s error=%s",
                log_username,
                user_uuid,
                e,
            )
            failed += 1
            continue
        except Exception as e:
            logging.error(
                "Failed to create user. username=%s uuid=%s error=%s",
                log_username,
                user_uuid,
                e,
            )
            failed += 1
            continue

    logging.info(
        "Done. created=%s skipped=%s failed=%s", created, skipped, failed
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
