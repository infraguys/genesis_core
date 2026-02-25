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
import sys

import requests


def _build_base_url(url: str) -> str:
    return url.rstrip("/")


def _get_admin_token(
    session: requests.Session,
    base_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    timeout: float,
) -> str:
    token_url = f"{base_url}/realms/{realm}/protocol/openid-connect/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    response = session.post(token_url, data=data, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(
            "Failed to obtain admin token from Keycloak. "
            f"status={response.status_code} body={response.text}"
        )
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Keycloak token response does not contain access_token")
    return token


def _extract_surname(user: dict) -> str | None:
    attributes = user.get("attributes")
    if not isinstance(attributes, dict):
        return None

    surname = attributes.get("surname")
    if isinstance(surname, list) and surname:
        return str(surname[0])
    if isinstance(surname, str):
        return surname

    return None


def _fetch_all_users(
    session: requests.Session,
    base_url: str,
    realm: str,
    token: str,
    page_size: int,
    timeout: float,
) -> list[dict]:
    users_url = f"{base_url}/admin/realms/{realm}/users"
    headers = {"Authorization": f"Bearer {token}"}

    first = 0
    result: list[dict] = []
    while True:
        params = {"first": first, "max": page_size}
        response = session.get(
            users_url, headers=headers, params=params, timeout=timeout
        )
        if response.status_code != 200:
            raise RuntimeError(
                "Failed to fetch users from Keycloak. "
                f"status={response.status_code} body={response.text}"
            )

        batch = response.json()
        if not isinstance(batch, list):
            raise RuntimeError("Keycloak users endpoint returned non-list JSON")

        if not batch:
            break

        for user in batch:
            if not isinstance(user, dict):
                continue
            result.append(
                {
                    "uuid": user.get("id"),
                    "username": user.get("username"),
                    "email": user.get("email"),
                    "firstname": user.get("firstName"),
                    "lastname": user.get("lastName"),
                    "surname": _extract_surname(user),
                }
            )

        if len(batch) < page_size:
            break

        first += page_size

    return result


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch all users from Keycloak (with pagination) and save them to JSON file.",
        epilog=(
            "Example:\n"
            "  fetch_keycloak_users.py --url https://kc.example.com --realm master "
            "--client-id admin-cli --client-secret secret --output users.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Keycloak base URL (without trailing slash), e.g. https://kc.example.com",
    )
    parser.add_argument("--realm", required=True, help="Realm name to fetch users from")
    parser.add_argument(
        "--client-id",
        required=True,
        help="OIDC client id used to obtain token",
    )
    parser.add_argument(
        "--client-secret",
        required=True,
        help="OIDC client secret used to obtain token",
    )
    parser.add_argument("--output", required=True, help="Output path for JSON file")
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Page size for Keycloak pagination (default: 100)",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    if args.page_size <= 0:
        raise ValueError("--page-size must be positive")
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")

    base_url = _build_base_url(args.url)

    session = requests.Session()
    session.verify = not args.insecure

    token = _get_admin_token(
        session=session,
        base_url=base_url,
        realm=args.realm,
        client_id=args.client_id,
        client_secret=args.client_secret,
        timeout=args.timeout,
    )

    users = _fetch_all_users(
        session=session,
        base_url=base_url,
        realm=args.realm,
        token=token,
        page_size=args.page_size,
        timeout=args.timeout,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
