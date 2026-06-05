"""Test fixture for TLS certificate generation with wildcard, added to global Certificate Manager and SSL Certificate.

Verify that an ECDSA P-256 certificate is generated with SANs entries for base- and wildcard- domain, and signed by an
ECDSA P-256 CA certificate. These Google Cloud resources are expected:
* Global Certificate Manager certificate
* Global Compute Engine SSL certificate
"""

import pathlib
from collections.abc import Callable, Generator
from typing import Any, cast

import pytest
from cryptography import x509
from google.cloud import certificate_manager_v1, compute_v1, secretmanager_v1

from tests import (
    assert_default_ca_cert,
    assert_default_cert,
    certificate_from_data,
    certificates_from_output,
    default_assert_certificate_manager_certificate,
    default_assert_key,
    default_assert_ssl_certificate,
    equal_asserter_builder,
    run_tf_plan_apply_destroy,
    unset_asserter,
)

FIXTURE_NAME = "wildcard"
FIXTURE_LABELS = {
    "fixture": FIXTURE_NAME,
}
FIXTURE_DOMAINS = [
    f"{FIXTURE_NAME}.example.com",
    f"*.{FIXTURE_NAME}.example.com",
]


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
                },
            },
            "certificate_manager": {
                "wildcard": {
                    "name": f"{fixture_name}-wildcard",
                    "description": f"Test wildcard certificate for {FIXTURE_NAME} scenario",
                },
            },
            "ssl_certificate": {
                "wildcard": {
                    "prefix": f"{fixture_name}-wildcard",
                    "description": f"Test wildcard certificate for {FIXTURE_NAME} scenario",
                },
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


def test_ca_cert(
    ca_cert: x509.Certificate,
) -> None:
    """Verify the CA certificate meets expectations."""
    assert_default_ca_cert(ca_cert=ca_cert)


def test_certificates(certificates: dict[str, x509.Certificate]) -> None:
    """Verify that the certificates from output match expectations."""
    assert certificates is not None
    assert len(certificates) == 1
    assert "wildcard" in certificates
    for cname, cert in certificates.items():
        assert_default_cert(cert=cert, cname_asserter=equal_asserter_builder(cname), expected_sans=FIXTURE_DOMAINS)


def assert_key(key: Any) -> None:  # noqa: ANN401
    """Raise an AssertionError if the private key does not match expectations."""
    default_assert_key(key)


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
    """Verify that no regional Secret Manager Secrets were created by querying the API directly."""
    result = list(list_regional_secret_manager_secrets(fixture_name))
    assert result is not None
    assert len(result) == 0


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
        default_assert_certificate_manager_certificate(
            cert=certificate,
            description_asserter=equal_asserter_builder(f"Test wildcard certificate for {FIXTURE_NAME} scenario"),
            expected_labels=fixture_labels,
            cname_asserter=equal_asserter_builder("wildcard"),
            expected_domains=FIXTURE_DOMAINS,
        )


def test_global_certificate_manager_certificates_count(
    list_global_certificate_manager_certificates: Callable[[str], list[certificate_manager_v1.Certificate]],
    fixture_name: str,
) -> None:
    """Verify that a single global Certificate Manager Certificate was created when the API is queried directly."""
    result = list(list_global_certificate_manager_certificates(fixture_name))
    assert result is not None
    assert len(result) == 1


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
    """Verify that the Compute Engine SSL Certificates meet expectations."""
    certificates = ssl_certificates_from_output(fixture_output)
    assert certificates is not None
    assert len(certificates) == 1
    for cname, certificate in certificates.items():
        assert cname == "wildcard"
        default_assert_ssl_certificate(
            cert=certificate,
            description_asserter=equal_asserter_builder(f"Test {cname} certificate for {FIXTURE_NAME} scenario"),
            cname_asserter=equal_asserter_builder(cname),
            expected_domains=FIXTURE_DOMAINS,
            region_asserter=unset_asserter,
        )


def test_global_ssl_certificates_count(
    list_global_ssl_certificates: Callable[[str], list[compute_v1.SslCertificate]],
    fixture_name: str,
) -> None:
    """Verify that a single global Compute Engine SSL Certificates was created when the API is queried directly."""
    result = list(list_global_ssl_certificates(fixture_name))
    assert result is not None
    assert len(result) == 1


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
