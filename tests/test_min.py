"""Test fixture for TLS certificate generation with minimal configuration options.

Verify that an ECDSA P-256 CA certificate is generated with expected subject. There should be no TLS certificates or
Google Cloud resources created.
"""

import pathlib
from collections.abc import Callable, Generator
from typing import Any, cast

import pytest
from cryptography import x509
from google.cloud import certificate_manager_v1, compute_v1, secretmanager_v1

from tests import (
    assert_default_ca_cert,
    certificate_from_data,
    certificates_from_output,
    run_tf_plan_apply_destroy,
)

FIXTURE_NAME = "min"
FIXTURE_LABELS = {
    "fixture": FIXTURE_NAME,
}


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
