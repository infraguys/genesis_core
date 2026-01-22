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
import logging

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
