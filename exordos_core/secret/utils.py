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
import secrets
import logging
import base64
import hashlib

from cryptography import exceptions
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

LOG = logging.getLogger(__name__)


def validate_openssh_key(key_data, password=None):
    """
    Validate an OpenSSH private key using cryptography library
    """
    if isinstance(key_data, str):
        key_data = key_data.encode()
    if isinstance(password, str):
        password = password.encode()
    try:
        serialization.load_ssh_private_key(
            key_data, password=password, backend=default_backend()
        )
        return True
    except (ValueError, TypeError, exceptions.UnsupportedAlgorithm):
        return False
    except Exception:
        LOG.exception("Something went wrong during key validation...")
        return False


def generate_salt(length: int = 16) -> str:
    """
    Generate a random salt string of specified length.

    Args:
        length: Length of the salt string (default: 16)

    Returns:
        Random salt string
    """
    return base64.b64encode(secrets.token_bytes(length)).decode()


def generate_hash_for_secret(secret: str, secret_salt: str, global_salt: str) -> str:
    """
    Generate a hash for a secret using PBKDF2.

    Args:
        secret: The secret to hash
        secret_salt: The salt for the secret
        global_salt: The global salt

    Returns:
        The hash of the secret
    """
    raw_secret_salt = base64.b64decode(secret_salt)
    raw_global_salt = base64.b64decode(global_salt)

    hashed = hashlib.pbkdf2_hmac(
        "sha512",
        secret.encode("utf-8"),
        raw_secret_salt + raw_global_salt,
        251685,  # count of iterations
    )

    return hashed.hex()


def generate_a256gcm_key() -> str:
    """
    Generate a random key for AES-256-GCM encryption.

    Returns:
        Base64 URL-safe encoded key string
    """
    raw_key = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(raw_key).decode().rstrip("=")
