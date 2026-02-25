"""Test fixture for Google managed TLS certificate generation with all configuration options.

No resources should be generated.
"""

import pathlib
from collections import Counter
from collections.abc import Callable, Generator
from typing import Any

import pytest
from google.cloud import certificate_manager_v1, compute_v1

from tests import run_tf_plan_apply_destroy

FIXTURE_NAME = "mgd-all"
FIXTURE_LABELS = {
    "fixture": FIXTURE_NAME,
}
FIXTURE_DOMAINS = [
    f"{FIXTURE_NAME}.example.com",
    f"{FIXTURE_NAME}.example.net",
]
FIXTURE_POLICY_CUSTOM_FEATURES = [
    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
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
    fixture_dir: Callable[[str], pathlib.Path],
    project_id: str,
    region: str,
    fixture_name: str,
    fixture_labels: dict[str, str],
) -> Generator[dict[str, Any], None, None]:
    """Create TLS resources for test case."""
    with run_tf_plan_apply_destroy(
        fixture=fixture_dir(FIXTURE_NAME),
        tfvars={
            "project_id": project_id,
            "labels": fixture_labels,
            "domains": FIXTURE_DOMAINS,
            "certificate_manager": {
                "name": fixture_name,
                "description": f"Test managed Certificate Manager Certificate for {FIXTURE_NAME} scenario",
                "region": region,
                "type": "PER_PROJECT_RECORD",
            },
            "ssl_certificate": {
                "name": fixture_name,
                "description": f"Test managed SSL Certificate for {FIXTURE_NAME} scenario",
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


def test_certificate_manager_certificate(
    certificate_manager_certificate_from_output: Callable[
        [dict[str, Any]],
        certificate_manager_v1.Certificate,
    ],
    fixture_labels: dict[str, str],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that a Certificate Manager Certificate is in the module output."""
    certificate = certificate_manager_certificate_from_output(fixture_output)
    assert certificate
    assert certificate.description == f"Test managed Certificate Manager Certificate for {FIXTURE_NAME} scenario"
    assert all(item in certificate.labels.items() for item in fixture_labels.items())
    assert not certificate.self_managed
    assert certificate.managed is not None
    assert Counter(certificate.managed.domains) == Counter(FIXTURE_DOMAINS)
    assert certificate.managed.dns_authorizations
    assert certificate.managed.state in [
        certificate_manager_v1.Certificate.ManagedCertificate.State.PROVISIONING,
        certificate_manager_v1.Certificate.ManagedCertificate.State.FAILED,
    ]
    assert certificate.scope == certificate_manager_v1.Certificate.Scope.DEFAULT


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
    assert len(result) == len(FIXTURE_DOMAINS)


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
    assert len(result) == 1


def test_ssl_certificates(
    ssl_certificate_from_output: Callable[[dict[str, Any]], compute_v1.SslCertificate | None],
    fixture_output: dict[str, Any],
) -> None:
    """Verify that a Compute Engine SSL Certificate is in the module output."""
    certificate = ssl_certificate_from_output(fixture_output)
    assert certificate
    assert certificate.description == f"Test managed SSL Certificate for {FIXTURE_NAME} scenario"
    assert certificate.managed is not None
    assert all(
        status in ["PROVISIONING_FAILED", "PROVISIONING"] for status in certificate.managed.domain_status.values()
    )
    assert Counter(certificate.managed.domains) == Counter(FIXTURE_DOMAINS)
    assert not certificate.region
    assert not certificate.self_managed


def test_global_ssl_certificates_count(
    list_global_ssl_certificates: Callable[[str], list[compute_v1.SslCertificate]],
    fixture_name: str,
) -> None:
    """Verify that a global Compute Engine SSL Certificate was created by querying the API directly."""
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
    region: str,
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
    """Verify that a regional Compute Engine SSL Policies was created by querying the API directly."""
    result = list(list_regional_ssl_policies(fixture_name))
    assert result is not None
    assert len(result) == 1
