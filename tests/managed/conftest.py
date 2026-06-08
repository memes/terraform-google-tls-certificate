"""Fixtures for testing the managed module."""

import pathlib
import shutil
from collections.abc import Callable
from typing import Any, cast

import pytest
from google.cloud import certificate_manager_v1, compute_v1, dns

from tests import skip_destroy_phase


@pytest.fixture(scope="session")
def fixture_dir(
    tmp_path_factory: pytest.TempPathFactory,
    backend_tf_builder: Callable[..., None],
    common_fixture_dir_ignores: Callable[[Any, list[str]], set[str]],
    managed_module_dir: pathlib.Path,
) -> Callable[[str], pathlib.Path]:
    """Return a builder that makes a copy of the managed module with backend configured appropriately."""

    def _builder(name: str) -> pathlib.Path:
        fixture_dir = tmp_path_factory.mktemp(name)
        shutil.copytree(
            src=managed_module_dir,
            dst=fixture_dir,
            dirs_exist_ok=True,
            ignore=common_fixture_dir_ignores,
        )
        backend_tf_builder(
            fixture_dir=fixture_dir,
            name=name,
        )
        return fixture_dir

    return _builder


@pytest.fixture(scope="session")
def list_global_certificate_manager_dns_authorizations(
    project_id: str,
    certificate_manager_client: certificate_manager_v1.CertificateManagerClient,
) -> Callable[[str], list[certificate_manager_v1.DnsAuthorization]]:
    """Return a function to list global Certificate Manager DNS Authorizations with names that begin with the value."""

    def _lister(name: str) -> list[certificate_manager_v1.DnsAuthorization]:
        result = certificate_manager_client.list_dns_authorizations(
            request=certificate_manager_v1.ListDnsAuthorizationsRequest(
                parent=f"projects/{project_id}/locations/global",
                filter=f"name:projects/{project_id}/locations/global/dnsAuthorizations/{name}",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def list_regional_certificate_manager_dns_authorizations(
    project_id: str,
    region: str,
    certificate_manager_client: certificate_manager_v1.CertificateManagerClient,
) -> Callable[[str], list[certificate_manager_v1.DnsAuthorization]]:
    """Return a function to list regional Certificate Manager DNS Authorizations with names that begin with value."""

    def _lister(name: str) -> list[certificate_manager_v1.DnsAuthorization]:
        result = certificate_manager_client.list_dns_authorizations(
            request=certificate_manager_v1.ListDnsAuthorizationsRequest(
                parent=f"projects/{project_id}/locations/{region}",
                filter=f"name:projects/{project_id}/locations/{region}/dnsAuthorizations/{name}",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def certificate_manager_certificate_from_output(
    certificate_manager_certificate_retriever: Callable[[str], certificate_manager_v1.Certificate],
) -> Callable[[dict[str, Any]], certificate_manager_v1.Certificate | None]:
    """Return a Certificate Manager Certificate from module output 'certificate_manager_id', or None."""

    def _extractor(fixture_output: dict[str, Any]) -> certificate_manager_v1.Certificate | None:
        cert_id = fixture_output.get("certificate_manager_id")
        if not cert_id:
            return None
        return certificate_manager_certificate_retriever(cert_id)

    return _extractor


@pytest.fixture(scope="session")
def ssl_certificate_from_output(
    ssl_certificate_retriever: Callable[[str], compute_v1.SslCertificate],
) -> Callable[[dict[str, Any]], compute_v1.SslCertificate | None]:
    """Return a Compute Engine SSL Certificate from output 'ssl_certificate_self_link' or None."""

    def _extractor(fixture_output: dict[str, Any]) -> compute_v1.SslCertificate | None:
        self_link = fixture_output.get("ssl_certificate_self_link")
        if not self_link:
            return None
        return ssl_certificate_retriever(self_link)

    return _extractor


@pytest.fixture(scope="session")
def dns_client(project_id: str) -> dns.Client:
    """Return a reusable DNS API client."""
    return dns.Client(
        project=project_id,
    )


@pytest.fixture(scope="session")
def dns_managed_zone_builder(
    request: pytest.FixtureRequest,
    dns_client: dns.Client,
) -> Callable[[str, str, str | None], dns.zone.ManagedZone]:
    """Return a function that will create a Cloud DNS Managed Zone."""

    def _builder(name: str, dns_name: str, description: str | None = None) -> dns.zone.ManagedZone:
        assert name
        assert dns_name
        if not dns_name.endswith("."):
            dns_name = f"{dns_name}."
        if description is None:
            description = "Test managed DNS zone for managed TLS certificates."
        zone = next((cast("dns.zone.ManagedZone", zone) for zone in dns_client.list_zones() if zone.name == name), None)
        if zone is None:
            zone = dns_client.zone(name=name, dns_name=dns_name, description=description)
            zone.create()

        def _cleanup() -> None:
            if not skip_destroy_phase():
                zone.delete()

        request.addfinalizer(_cleanup)
        return zone

    return _builder
