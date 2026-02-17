"""Test fixture for Google managed TLS certificate generation with minimal configuration options.

No resources should be generated.
"""

import pathlib
from collections.abc import Callable, Generator
from typing import Any

import pytest
from google.cloud import certificate_manager_v1, compute_v1

from tests import run_tf_plan_apply_destroy

FIXTURE_NAME = "mgd-min"
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
    fixture_dir: Callable[[str], pathlib.Path],
    project_id: str,
) -> Generator[dict[str, Any], None, None]:
    """Create TLS resources for test case."""
    with run_tf_plan_apply_destroy(
        fixture=fixture_dir(FIXTURE_NAME),
        tfvars={
            "project_id": project_id,
        },
    ) as output:
        yield output


def test_certificate_manager_certificate(
    certificate_manager_certificate_from_output: Callable[
        [dict[str, Any]],
        certificate_manager_v1.Certificate,
    ],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that no Certificate Manager Certificates are in the module output."""
    assert certificate_manager_certificate_from_output(fixture_output) is None


def test_global_certificate_manager_dns_authorizations_count(
    list_global_certificate_manager_dns_authorizations: Callable[[str], list[certificate_manager_v1.DnsAuthorization]],
    fixture_name: str,
) -> None:
    """Verify that no global Certificate Manager DNS Authorizations were created by querying the API directly."""
    result = list(list_global_certificate_manager_dns_authorizations(fixture_name))
    assert result is not None
    assert len(result) == 0


def test_regional_certificate_manager_dns_authorizations_count(
    list_regional_certificate_manager_dns_authorizations: Callable[
        [str],
        list[certificate_manager_v1.DnsAuthorization],
    ],
    fixture_name: str,
) -> None:
    """Verify that no regional Certificate Manager DNS Authorizations were created by querying the API directly."""
    result = list(list_regional_certificate_manager_dns_authorizations(fixture_name))
    assert result is not None
    assert len(result) == 0


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
    ssl_certificate_from_output: Callable[[dict[str, Any]], compute_v1.SslCertificate | None],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that Compute Engine SSL Certificates are not in the module output."""
    assert ssl_certificate_from_output(fixture_output) is None


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
