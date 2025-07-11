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

import os
import time
import logging
import typing as tp

from acme import challenges
from acme import client as acme_lib_client
from acme import crypto_util
from acme import errors
from acme import messages
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import josepy as jose

from genesis_core.agent.universal.drivers.secret.backend import (
    clients as dns_clients,
)

LOG = logging.getLogger(__name__)


# This is the staging point for ACME-V2 within Let's Encrypt.
DIRECTORY_URL = "https://acme-staging-v02.api.letsencrypt.org/directory"
USER_AGENT = "python-acme-example"

# Account key size
ACC_KEY_BITS = 2048

# Certificate private key size
CERT_PKEY_BITS = 2048


# мы уже должны иметь где-то сохранённый приватный ключ
# new_client_key = rsa.generate_private_key(
#     public_exponent=65537, key_size=ACC_KEY_BITS, backend=default_backend()
# )

# raw_client_key = new_client_key.private_bytes(
#     encoding=serialization.Encoding.PEM,
#     format=serialization.PrivateFormat.PKCS8,
#     encryption_algorithm=serialization.NoEncryption(),
# )

# # пример как вычитать ключ
# client_key = serialization.load_pem_private_key(
#     raw_client_key, password=None, backend=default_backend()
# )


def get_or_create_client_private_key(key_path: str) -> rsa.RSAPrivateKey:
    """Get or create a client private key."""
    # Try to get the private key
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

    # If it doesn't exist, create it
    os.makedirs(os.path.dirname(key_path), exist_ok=True)

    new_client_key = rsa.generate_private_key(
        public_exponent=65537, key_size=ACC_KEY_BITS, backend=default_backend()
    )
    raw_client_key = new_client_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Save the private key
    with open(key_path, "wb") as f:
        f.write(raw_client_key)

    return serialization.load_pem_private_key(
        raw_client_key, password=None, backend=default_backend()
    )


# def acme_get_client(
#     private_client_key, user_agent=USER_AGENT, directory_url=DIRECTORY_URL
# ):
#     acc_key = jose.JWKRSA(key=private_client_key)

#     net = client.ClientNetwork(acc_key, user_agent=user_agent)
#     directory = client.ClientV2.get_directory(directory_url, net)
#     return client.ClientV2(directory, net=net)


# по идее нужно только один раз
# def register_new_acme(acme_client, email):
#     return acme_client.new_account(
#         messages.Registration.from_data(
#             email=email, terms_of_service_agreed=True
#         )
#     )


# acme_client = acme_get_client(client_key)

# email = "some@email.com"

# acme_client.net.account = register_new_acme(acme_client, email)
# ИЛИ
# acme_client.query_registration(
#     messages.Registration.from_data(email=email, terms_of_service_agreed=True)
# )


def get_acme_client(
    private_client_key: rsa.RSAPrivateKey,
    email: str,
    user_agent: str = USER_AGENT,
    directory_url: str = DIRECTORY_URL,
) -> acme_lib_client.ClientV2:
    """Get ACME client."""
    acc_key = jose.JWKRSA(key=private_client_key)

    net = acme_lib_client.ClientNetwork(acc_key, user_agent=user_agent)
    directory = acme_lib_client.ClientV2.get_directory(directory_url, net)
    client = acme_lib_client.ClientV2(directory, net=net)
    client.query_registration(
        messages.Registration.from_data(
            email=email, terms_of_service_agreed=True
        )
    )
    return client


def new_csr_comp(
    domains_name: tp.Collection[str], pkey_pem: bytes | None = None
) -> tuple[bytes, bytes]:
    """Create certificate signing request."""
    if pkey_pem is None:
        # Create private key.
        pkey = rsa.generate_private_key(
            public_exponent=65537, key_size=CERT_PKEY_BITS
        )
        pkey_pem = pkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    csr_pem = crypto_util.make_csr(pkey_pem, list(domains_name))
    return pkey_pem, csr_pem


def select_dns01_chall(orderr: messages.OrderResource) -> challenges.DNS01:
    """Extract authorization resource from within order resource."""
    # Authorization Resource: authz.
    # This object holds the offered challenges by the server and their status.
    authz_list = orderr.authorizations

    for authz in authz_list:
        # Choosing challenge.
        # authz.body.challenges is a set of ChallengeBody objects.
        for i in authz.body.challenges:
            # Find the supported challenge.
            if isinstance(i.chall, challenges.DNS01):
                return i

    raise Exception("DNS-01 challenge was not offered by the CA server.")


def perform_dns01(
    domains: tp.Collection[str],
    acme_client: acme_lib_client.ClientV2,
    dns_client: dns_clients.TinyDNSCoreClient,
    challb: challenges.DNS01,
    orderr: messages.OrderResource,
) -> str:
    """Set up standalone webserver and perform DNS-01 challenge."""

    response, validation = challb.response_and_validation(acme_client.net.key)

    # Go to Core DNS and add TXT record
    for domain in domains:
        dns_client.create_txt_record(
            domain, f"_acme-challenge.{domain}", validation.decode("utf-8")
        )

    # input(
    #     f"Add DNS TXT record and press Enter when ready:\n"
    #     f"TXT Record Name: _acme-challenge.{domain}\n"
    #     f"Value: {validation}\n"
    # )

    # Replace it with retries
    LOG.info("Waiting 20 seconds for DNS propagation...")
    time.sleep(20)

    # Let the CA server know that we are ready for the challenge.
    acme_client.answer_challenge(challb, response)

    # Wait for challenge status and then issue a certificate.
    # It is possible to set a deadline time.
    finalized_orderr = acme_client.poll_and_finalize(orderr)

    return finalized_orderr.fullchain_pem


def create_cert(
    acme_client: acme_lib_client.ClientV2,
    dns_client: dns_clients.TinyDNSCoreClient,
    domains: tp.Collection[str],
) -> tuple[bytes, bytes, str]:
    """Issue a new certificate."""
    # Create domain private key and CSR
    pkey_pem, csr_pem = new_csr_comp(domains)

    # Issue certificate
    orderr = acme_client.new_order(csr_pem)

    # Select DNS-01 within offered challenges by the CA server
    challb = select_dns01_chall(orderr)

    # The certificate is ready to be used in the variable "fullchain_pem".
    fullchain_pem = perform_dns01(
        domains, acme_client, dns_client, challb, orderr
    )

    return pkey_pem, csr_pem, fullchain_pem


def renew_cert(
    acme_client: acme_lib_client.ClientV2,
    dns_client: dns_clients.TinyDNSCoreClient,
    domains: tp.Collection[str],
    pkey_pem: bytes,
) -> tuple[bytes, bytes, str]:
    """Renew the certificate with the specified private key."""
    _, csr_pem = new_csr_comp(domains, pkey_pem)
    orderr = acme_client.new_order(csr_pem)
    challb = select_dns01_chall(orderr)

    # Performing challenge
    fullchain_pem = perform_dns01(
        domains, acme_client, dns_client, challb, orderr
    )

    return pkey_pem, csr_pem, fullchain_pem


def revoke_cert(
    acme_client: acme_lib_client.ClientV2, fullchain_pem: str
) -> None:
    """Revoke the certificate."""
    fullchain_com = x509.load_pem_x509_certificate(fullchain_pem.encode())

    try:
        # revocation reason = 0
        acme_client.revoke(fullchain_com, 0)
    except errors.ConflictError:
        # Certificate already revoked.
        pass
