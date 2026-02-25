"""Test fixture for TLS certificate generation with all configuration options set.

Verify that an RSA-2048 TLS certificate is generated with SANs entries for RFC1918 addresses and wildcard domain, signed
by an RSA-2048 P-256 CA certificate. These Google Cloud resources are expected:
* Secret Manager secret the TLS key
* Secret Manager secret for TLS cert
* Secret Manager secret with JSON encoded key and cert
* Regional Certificate Manager certificate
* Regional Compute Engine SSL certificate
* Regional Compute Engine SSL Policy with CUSTOM profile and two FIPS ciphers
"""

import json
import pathlib
from collections import Counter
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.cloud import certificate_manager_v1, compute_v1, resourcemanager_v3, secretmanager_v1

from tests import (
    AsserterFunc,
    certificate_from_data,
    certificates_from_output,
    equal_asserter_builder,
    has_value_asserter,
    run_tf_plan_apply_destroy,
)

FIXTURE_NAME = "all"
FIXTURE_LABELS = {
    "fixture": FIXTURE_NAME,
}
FIXTURE_DOMAINS = [
    f"{FIXTURE_NAME}.example.com",
    f"{FIXTURE_NAME}.example.net",
]
FIXTURE_IP_ADDRESSES = [
    "10.10.10.10",
    "10.10.10.11",
]
FIXTURE_POLICY_CUSTOM_FEATURES = [
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
]
EXPECTED_RSA_KEY_LENGTH = 4096


@pytest.fixture(scope="module")
def fixture_name(prefix: str) -> str:
    """Return the name to use for resources in this module."""
    return f"{prefix}-{FIXTURE_NAME}"


@pytest.fixture(scope="module")
def fixture_labels(labels: dict[str, str]) -> dict[str, str]:
    """Return a dict of labels for this test module."""
    return FIXTURE_LABELS | labels


@pytest.fixture(scope="module")
def fixture_output(
    root_fixture_dir: Callable[[str], pathlib.Path],
    project_id: str,
    region: str,
    fixture_name: str,
    fixture_labels: str,
) -> Generator[dict[str, Any], None, None]:
    """Create TLS resources for test case."""
    with run_tf_plan_apply_destroy(
        fixture=root_fixture_dir(FIXTURE_NAME),
        tfvars={
            "project_id": project_id,
            "labels": fixture_labels,
            "annotations": fixture_labels,
            "requests": {
                "wildcard": {
                    "dns_names": FIXTURE_DOMAINS,
                    "ip_addresses": FIXTURE_IP_ADDRESSES,
                },
            },
            "subject": {
                "common_name": "Test CA for all options",
                "organization": "Test organization",
                "organizational_unit": "Test organizational unit",
                "locality": "Test locality",
                "province": "Test province",
                "country": "XX",
            },
            "tls_options": {
                "key_type": "RSA-4096",
                "ttl_hours": 100,
                "allowed_uses": [
                    "digital_signature",
                    "server_auth",
                    "client_auth",
                    "any_extended",
                ],
            },
            "secret_manager": {
                "wildcard": {
                    "prefix": f"{fixture_name}-wildcard",
                    "region": region,
                    "key": True,
                    "cert": True,
                    "json": True,
                },
            },
            "certificate_manager": {
                "wildcard": {
                    "name": f"{fixture_name}-wildcard",
                    "region": region,
                    "description": f"Test wildcard certificate for {FIXTURE_NAME} scenario",
                },
            },
            "ssl_certificate": {
                "wildcard": {
                    "prefix": f"{fixture_name}-wildcard",
                    "region": region,
                    "description": f"Test wildcard certificate for {FIXTURE_NAME} scenario",
                },
            },
            "ssl_policy": {
                "name": fixture_name,
                "description": f"Test SSL policy for {FIXTURE_NAME} scenario",
                "region": region,
                "profile": "CUSTOM",
                "min_tls_version": "TLS_1_1",
                "custom_features": FIXTURE_POLICY_CUSTOM_FEATURES,
            },
        },
    ) as output:
        yield output


@pytest.fixture(scope="module")
def ca_cert(fixture_output: dict[str, Any]) -> x509.Certificate | None:
    """Return a Certificate object built from the module output 'ca_cert' or None."""
    return certificate_from_data(cast("str", fixture_output["ca_cert"])) if "ca_cert" in fixture_output else None


@pytest.fixture(scope="module")
def certificates(fixture_output: dict[str, Any]) -> dict[str, x509.Certificate]:
    """Return a map of common name to x509 Certificate from module output."""
    return certificates_from_output(fixture_output)


def assert_ca_cert(
    ca_cert: x509.Certificate | None,
) -> None:
    """Raise an AssertionError if the CA certificate does not meet expectations."""
    assert ca_cert is not None
    assert ca_cert.not_valid_before_utc < datetime.now(UTC)
    assert ca_cert.not_valid_after_utc > datetime.now(UTC)
    assert isinstance(ca_cert.public_key(), rsa.RSAPublicKey)
    assert cast("rsa.RSAPublicKey", ca_cert.public_key()).key_size == EXPECTED_RSA_KEY_LENGTH
    assert ca_cert.subject
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.COMMON_NAME, value="Test CA for all options"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATION_NAME, value="Test organization"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATIONAL_UNIT_NAME, value="Test organizational unit"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.LOCALITY_NAME, value="Test locality"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.STATE_OR_PROVINCE_NAME, value="Test province"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.COUNTRY_NAME, value="XX"),
    ]
    assert ca_cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca


def assert_cert(
    cert: x509.Certificate | None,
    cname_asserter: AsserterFunc | None = None,
) -> None:
    """Raise an AssertionError if the Certificate does not meet expectations."""
    if cname_asserter is None:
        cname_asserter = has_value_asserter
    assert cert
    assert cert.not_valid_before_utc < datetime.now(UTC)
    assert cert.not_valid_after_utc > datetime.now(UTC)
    assert isinstance(cert.public_key(), rsa.RSAPublicKey)
    assert cast("rsa.RSAPublicKey", cert.public_key()).key_size == EXPECTED_RSA_KEY_LENGTH
    assert cert.subject
    cname = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    assert len(cname) == 1
    cname_asserter(cname[0].value)
    assert cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATION_NAME, value="Test organization"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATIONAL_UNIT_NAME, value="Test organizational unit"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.LOCALITY_NAME, value="Test locality"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.STATE_OR_PROVINCE_NAME, value="Test province"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.COUNTRY_NAME, value="XX"),
    ]
    assert not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    assert cert.extensions.get_extension_for_class(x509.KeyUsage).value == x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )
    assert cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value == x509.ExtendedKeyUsage(
        [
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            x509.oid.ExtendedKeyUsageOID.ANY_EXTENDED_KEY_USAGE,
        ],
    )


def test_ca_cert(
    ca_cert: x509.Certificate,
) -> None:
    """Verify the CA certificate meets expectations."""
    assert_ca_cert(ca_cert=ca_cert)


def test_certificates(certificates: dict[str, x509.Certificate]) -> None:
    """Verify that the certificates from output match expectations."""
    assert certificates is not None
    assert len(certificates) == 1
    assert "wildcard" in certificates
    for cname, cert in certificates.items():
        assert_cert(cert=cert, cname_asserter=equal_asserter_builder(cname))


def assert_key(key: Any) -> None:  # noqa: ANN401
    """Raise an AssertionError if the private key does not match expectations."""
    assert key is not None
    assert isinstance(key, rsa.RSAPrivateKey)
    assert key.key_size == EXPECTED_RSA_KEY_LENGTH


def test_secrets(
    project_details: resourcemanager_v3.Project,
    region: str,
    secret_manager_secrets_from_output: Callable[[dict[str, Any]], dict[str, dict[str, secretmanager_v1.Secret]]],
    secret_manager_secret_version_is_enabled: Callable[..., bool],
    secret_manager_secret_version_payload_retriever: Callable[..., bytes],
    fixture_name: str,
    fixture_labels: dict[str, str],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that Secret Manager Secrets were created as expected."""
    secrets = secret_manager_secrets_from_output(fixture_output)
    assert secrets is not None
    assert len(secrets) == 1
    for cname, entries in secrets.items():
        assert cname == "wildcard"
        for entry in ["key", "cert", "json"]:
            secret = entries[entry]
            assert secret
            assert secret.name == f"{project_details.name}/locations/{region}/secrets/{fixture_name}-{cname}-{entry}"
            assert all(item in secret.labels.items() for item in fixture_labels.items())
            assert all(item in secret.annotations.items() for item in fixture_labels.items())
            assert secret_manager_secret_version_is_enabled(secret)
            payload = secret_manager_secret_version_payload_retriever(secret)
            if entry == "key":
                assert_key(serialization.load_pem_private_key(payload, password=None))
            elif entry == "cert":
                assert_cert(
                    cert=x509.load_pem_x509_certificate(data=payload),
                    cname_asserter=equal_asserter_builder(cname),
                )
            else:
                json_payload = cast("dict[str, str]", json.loads(payload))
                assert "cert" in json_payload
                assert_cert(
                    x509.load_pem_x509_certificate(json_payload["cert"].encode("utf-8")),
                    cname_asserter=equal_asserter_builder(cname),
                )
                assert "key" in json_payload
                assert_key(serialization.load_pem_private_key(json_payload["key"].encode("utf-8"), password=None))


def test_global_secret_manager_secrets_count(
    list_global_secret_manager_secrets: Callable[[str], list[secretmanager_v1.Secret]],
    fixture_name: str,
) -> None:
    """Verify that no global Secret Manager Secrets were created by querying the API directly."""
    result = list(list_global_secret_manager_secrets(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_regional_secret_manager_secrets_count(
    list_regional_secret_manager_secrets: Callable[[str], list[secretmanager_v1.Secret]],
    fixture_name: str,
) -> None:
    """Verify that a single regional Secret Manager Secret was created when the API is queried directly."""
    result = list(list_regional_secret_manager_secrets(fixture_name))
    assert result is not None
    assert len(result) == 3  # noqa: PLR2004


def test_certificate_manager_certificates(
    certificate_manager_certificates_from_output: Callable[
        [dict[str, Any]],
        dict[str, certificate_manager_v1.Certificate],
    ],
    fixture_labels: dict[str, str],
    fixture_output: dict[str, Any],
) -> None:
    """Verify the Certificate Manager Certificates were created as expected."""
    certificates = certificate_manager_certificates_from_output(fixture_output)
    assert certificates is not None
    assert len(certificates) == 1
    for cname, certificate in certificates.items():
        assert cname == "wildcard"
        assert certificate
        assert certificate.description == f"Test {cname} certificate for {FIXTURE_NAME} scenario"
        assert all(item in certificate.labels.items() for item in fixture_labels.items())
        assert certificate.self_managed is not None
        assert not certificate.self_managed.pem_certificate
        assert not certificate.self_managed.pem_private_key
        assert not certificate.managed
        assert Counter(certificate.san_dnsnames) == Counter(FIXTURE_DOMAINS)
        assert certificate.pem_certificate
        certs_in_chain = x509.load_pem_x509_certificates(certificate.pem_certificate.encode(encoding="utf-8"))
        assert len(certs_in_chain) == 2  # noqa: PLR2004
        assert_cert(cert=certs_in_chain[0], cname_asserter=equal_asserter_builder(cname))
        assert_ca_cert(certs_in_chain[1])
        assert certificate.scope == certificate_manager_v1.Certificate.Scope.DEFAULT


def test_global_certificate_manager_certificates_count(
    list_global_certificate_manager_certificates: Callable[[str], list[certificate_manager_v1.Certificate]],
    fixture_name: str,
) -> None:
    """Verify that no global Certificate Manager Certificates were created by querying the API directly."""
    result = list(list_global_certificate_manager_certificates(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_regional_certificate_manager_certificates_count(
    list_regional_certificate_manager_certificates: Callable[[str], list[certificate_manager_v1.Certificate]],
    fixture_name: str,
) -> None:
    """Verify that a single regional Certificate Manager Certificate was created when the API is queried directly."""
    result = list(list_regional_certificate_manager_certificates(fixture_name))
    assert result is not None
    assert len(result) == 1


def test_ssl_certificates(
    region: str,
    ssl_certificates_from_output: Callable[[dict[str, Any]], dict[str, compute_v1.SslCertificate]],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that the Compute Engine SSL Certificates meet expectations."""
    certificates = ssl_certificates_from_output(fixture_output)
    assert certificates is not None
    assert len(certificates) == 1
    for cname, certificate in certificates.items():
        assert cname == "wildcard"
        assert certificate
        assert certificate.description == f"Test {cname} certificate for {FIXTURE_NAME} scenario"
        assert certificate.self_managed is not None
        assert certificate.self_managed.certificate
        assert not certificate.self_managed.private_key
        assert not certificate.managed
        assert certificate.region.split("/")[-1] == region
        assert Counter(certificate.subject_alternative_names) == Counter(FIXTURE_DOMAINS)
        assert not certificate.private_key
        assert certificate.certificate
        certs_in_chain = x509.load_pem_x509_certificates(certificate.certificate.encode(encoding="utf-8"))
        assert len(certs_in_chain) == 2  # noqa: PLR2004
        assert_cert(cert=certs_in_chain[0], cname_asserter=equal_asserter_builder(cname))
        assert_ca_cert(certs_in_chain[1])


def test_global_ssl_certificates_count(
    list_global_ssl_certificates: Callable[[str], list[compute_v1.SslCertificate]],
    fixture_name: str,
) -> None:
    """Verify that no global Compute Engine SSL Certificates were created by querying the API directly."""
    result = list(list_global_ssl_certificates(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_regional_ssl_certificates_count(
    list_regional_ssl_certificates: Callable[[str], list[compute_v1.SslCertificate]],
    fixture_name: str,
) -> None:
    """Verify that a single regional Compute Engine SSL Certificates was created when the API is queried directly."""
    result = list(list_regional_ssl_certificates(fixture_name))
    assert result is not None
    assert len(result) == 1


def test_ssl_policy(
    region: str,
    ssl_policy_from_output: Callable[[dict[str, Any]], compute_v1.SslPolicy | None],
    fixture_name: str,
    fixture_output: dict[str, Any],
) -> None:
    """Verify an SSL Policy self-link is in the module output."""
    policy = ssl_policy_from_output(fixture_output)
    assert policy is not None
    assert policy.name == fixture_name
    assert policy.description == f"Test SSL policy for {FIXTURE_NAME} scenario"
    assert policy.region.split("/")[-1] == region
    assert policy.min_tls_version == "TLS_1_1"
    assert policy.profile == "CUSTOM"
    assert policy.custom_features
    assert Counter(policy.custom_features) == Counter(FIXTURE_POLICY_CUSTOM_FEATURES)


def test_global_ssl_policies_count(
    list_global_ssl_policies: Callable[[str], list[compute_v1.SslPolicy]],
    fixture_name: str,
) -> None:
    """Verify that no global Compute Engine SSL Policies were created by querying the API directly."""
    result = list(list_global_ssl_policies(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_regional_ssl_policies_count(
    list_regional_ssl_policies: Callable[[str], list[compute_v1.SslPolicy]],
    fixture_name: str,
) -> None:
    """Verify that a single regional Compute Engine SSL Policies was created by querying the API directly."""
    result = list(list_regional_ssl_policies(fixture_name))
    assert result is not None
    assert len(result) == 1
