"""Test fixture for RSA TLS certificate generation with minimal configuration options.

Verify that an RSA-2048 CA certificate is generated with expected subject. There should be no TLS certificates or Google
Cloud resources created.
"""

import pathlib
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from google.cloud import certificate_manager_v1, compute_v1, secretmanager_v1

from tests import (
    DEFAULT_CA_CNAME,
    AsserterFunc,
    certificate_from_data,
    certificates_from_output,
    equal_asserter_builder,
    run_tf_plan_apply_destroy,
)

FIXTURE_NAME = "min-rsa"
FIXTURE_LABELS = {
    "fixture": FIXTURE_NAME,
}
EXPECTED_RSA_KEY_LENGTH = 2048


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
) -> Generator[dict[str, Any], None, None]:
    """Create TLS resources for test case."""
    with run_tf_plan_apply_destroy(
        fixture=root_fixture_dir(FIXTURE_NAME),
        tfvars={
            "project_id": project_id,
            "tls_options": {
                "key_type": "RSA-2048",
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
    cname_asserter: AsserterFunc | None = None,
) -> None:
    """Raise an AssertionError if the Certificate object does not meet expectations for default CA certificate."""
    if cname_asserter is None:
        cname_asserter = equal_asserter_builder(DEFAULT_CA_CNAME)
    assert ca_cert
    assert ca_cert.not_valid_before_utc < datetime.now(UTC)
    assert ca_cert.not_valid_after_utc > datetime.now(UTC)
    assert isinstance(ca_cert.public_key(), rsa.RSAPublicKey)
    assert cast("rsa.RSAPublicKey", ca_cert.public_key()).key_size == EXPECTED_RSA_KEY_LENGTH
    assert ca_cert.subject
    cname = ca_cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    assert len(cname) == 1
    cname_asserter(cname[0].value)
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATION_NAME, value="F5, Inc"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATIONAL_UNIT_NAME, value="F5 DevCentral Demos"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.LOCALITY_NAME, value="Seattle"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.STATE_OR_PROVINCE_NAME, value="Washington"),
    ]
    assert ca_cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.COUNTRY_NAME, value="US"),
    ]
    assert ca_cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca


def test_ca_cert(
    ca_cert: x509.Certificate,
) -> None:
    """Verify the CA certificate meets expectations."""
    assert_ca_cert(ca_cert=ca_cert)


def test_certificates(certificates: dict[str, x509.Certificate]) -> None:
    """Verify that no TLS certificates are in the module output."""
    assert certificates is not None
    assert len(certificates) == 0


def test_secrets(
    secret_manager_secrets_from_output: Callable[[dict[str, Any]], dict[str, dict[str, secretmanager_v1.Secret]]],
    fixture_output: dict[str, Any],
) -> None:
    """Verify no Secret Manager Secrets are in the module output."""
    secrets = secret_manager_secrets_from_output(fixture_output)
    assert secrets is not None
    assert len(secrets) == 0


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
    """Verify that no regional Secret Manager Secret were created by querying the API directly."""
    result = list(list_regional_secret_manager_secrets(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_certificate_manager_certificates(
    certificate_manager_certificates_from_output: Callable[
        [dict[str, Any]],
        dict[str, certificate_manager_v1.Certificate],
    ],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that no Certificate Manager Certificates are in the module output."""
    certificates = certificate_manager_certificates_from_output(fixture_output)
    assert certificates is not None
    assert len(certificates) == 0


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
    """Verify that no regional Certificate Manager Certificates were created by querying the API directly."""
    result = list(list_regional_certificate_manager_certificates(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_ssl_certificates(
    ssl_certificates_from_output: Callable[[dict[str, Any]], dict[str, compute_v1.SslCertificate]],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that Compute Engine SSL Certificates are not in the module output."""
    certificates = ssl_certificates_from_output(fixture_output)
    assert certificates is not None
    assert len(certificates) == 0


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
    """Verify that no regional Compute Engine SSL Certificates were created by querying the API directly."""
    result = list(list_regional_ssl_certificates(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_ssl_policy(
    ssl_policy_from_output: Callable[[dict[str, Any]], compute_v1.SslPolicy | None],
    fixture_output: dict[str, Any],
) -> None:
    """Verify an SSL Policy self-link is not in the module output."""
    assert ssl_policy_from_output(fixture_output) is None


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
    """Verify that no regional Compute Engine SSL Policies were created by querying the API directly."""
    result = list(list_regional_ssl_policies(fixture_name))
    assert result is not None
    assert len(result) == 0
