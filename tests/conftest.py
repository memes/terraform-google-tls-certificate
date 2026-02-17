"""Common testing fixtures."""

import os
import pathlib
import re
import shutil
from collections.abc import Callable
from typing import Any, cast

import google.auth
import google.auth.credentials
import pytest
from google.api_core import client_options, exceptions
from google.cloud import certificate_manager_v1, compute_v1, iam_admin_v1, resourcemanager_v3, secretmanager_v1

from tests import skip_destroy_phase

DEFAULT_PREFIX = "tls"
DEFAULT_LABELS = {
    "use_case": "automated-tofu-testing",
    "module": "terraform-google-tls-certificate",
    "driver": "pytest",
}
DEFAULT_REGION = "us-west1"
DEFAULT_TF_STATE_PREFIX = "tests/terraform-google-tls-certificate"
GLOBAL_SSL_CERTIFICATE_SELF_LINK_PATTERN = re.compile(
    r"projects/([a-z][a-z0-9-]{4,28}[a-z0-9])/global/sslCertificates/(.*)$",
)
REGIONAL_SSL_CERTIFICATE_SELF_LINK_PATTERN = re.compile(
    r"projects/([a-z][a-z0-9-]{4,28}[a-z0-9])/regions/([a-z][a-z-]+[a-z][0-9])/sslCertificates/(.*)$",
)
DEFAULT_TF_STATE_PREFIX = "tests/terraform-google-tls-certificate"
GLOBAL_SSL_POLICY_SELF_LINK_PATTERN = re.compile(
    r"projects/([a-z][a-z0-9-]{4,28}[a-z0-9])/global/sslPolicies/(.*)$",
)
REGIONAL_SSL_POLICY_SELF_LINK_PATTERN = re.compile(
    r"projects/([a-z][a-z0-9-]{4,28}[a-z0-9])/regions/([a-z][a-z-]+[a-z][0-9])/sslPolicies/(.*)$",
)


@pytest.fixture(scope="session")
def prefix() -> str:
    """Return the prefix to use for test resources.

    Preference will be given to the environment variable TEST_PREFIX with default value of 'tls'.
    """
    prefix = os.getenv("TEST_PREFIX", DEFAULT_PREFIX)
    if prefix:
        prefix = prefix.strip()
    if not prefix:
        prefix = DEFAULT_PREFIX
    assert prefix
    return prefix


@pytest.fixture(scope="session")
def project_id() -> str:
    """Return the project id to use for tests.

    Preference will be given to the environment variables TEST_GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_PROJECT followed by
    the default project identifier associated with local ADC credentials.
    """
    project_id = os.getenv("TEST_GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id:
        project_id = project_id.strip()
    if not project_id:
        _, project_id = google.auth.default()
    assert project_id
    return project_id


@pytest.fixture(scope="session")
def labels() -> dict[str, str]:
    """Return a dict of labels to apply to resources from environment variable TEST_GOOGLE_LABELS.

    If the environment variable TEST_GOOGLE_LABELS is not empty and can be parsed as a comma-separated list of key:value
    pairs then return a dict of keys to values.
    """
    raw = os.getenv("TEST_GOOGLE_LABELS")
    if not raw:
        return DEFAULT_LABELS
    return DEFAULT_LABELS | dict([x.split(":") for x in raw.split(",")])


@pytest.fixture(scope="session")
def region() -> str:
    """Return the Compute Engine region to use for tests.

    Preference will be given to the environment variable TEST_GOOGLE_REGION with fallback to the default value of
    'us-central1'.
    """
    region = os.getenv("TEST_GOOGLE_REGION", DEFAULT_REGION)
    if region:
        region = region.strip()
    if not region:
        region = DEFAULT_REGION
    assert region
    return region


@pytest.fixture(scope="session")
def tf_state_bucket() -> str:
    """Return the Google Cloud Storage bucket name to use for tofu/terraform state files."""
    bucket = os.getenv("TEST_GOOGLE_TF_STATE_BUCKET")
    if bucket:
        bucket = bucket.strip()
    assert bucket
    return bucket


@pytest.fixture(scope="session")
def tf_state_prefix() -> str:
    """Return the prefix to use for tofu/terraform state files in bucket.

    Preference will be given to the variable TEST_GOOGLE_TF_STATE_PREFIX with fallback to the default value of
    'tests/terraform-google-f5-bigip-ha'.
    """
    prefix = os.getenv("TEST_GOOGLE_TF_STATE_PREFIX", DEFAULT_TF_STATE_PREFIX)
    if prefix:
        prefix = prefix.strip()
    if not prefix:
        prefix = DEFAULT_TF_STATE_PREFIX
    assert prefix
    return prefix


@pytest.fixture(scope="session")
def backend_tf_builder(tf_state_bucket: str, tf_state_prefix: str) -> Callable[[pathlib.Path, str], None]:
    """Create or overwrite a _backend.tf file in the provided fixture_dir that configures GCS backend for state."""

    def _backend_tf(fixture_dir: pathlib.Path, name: str) -> None:
        assert fixture_dir.exists()
        assert name
        fixture_dir.joinpath("_backend.tf").write_text(
            "\n".join(
                [
                    "terraform {",
                    '  backend "gcs" {',
                    f'    bucket = "{tf_state_bucket}"',
                    f'    prefix = "{tf_state_prefix}/{name}"',
                    "  }",
                    "}",
                ],
            ),
        )

    return _backend_tf


@pytest.fixture(scope="session")
def common_fixture_dir_ignores() -> Callable[[Any, list[str]], set[str]]:
    """Return a set of ignore patterns that are unrelated to module sources or supporting files."""
    return shutil.ignore_patterns(".*", "*.md", "*.toml", "uv.lock", "tests")


@pytest.fixture(scope="session")
def root_module_dir() -> pathlib.Path:
    """Return the Path of the root module."""
    root_module_dir = pathlib.Path(__file__).parent.parent.resolve()
    assert root_module_dir.exists()
    assert root_module_dir.is_dir()
    assert root_module_dir.joinpath("main.tf").exists()
    assert root_module_dir.joinpath("outputs.tf").exists()
    assert root_module_dir.joinpath("variables.tf").exists()
    return root_module_dir


@pytest.fixture(scope="session")
def managed_module_dir() -> pathlib.Path:
    """Return the Path of the managed module."""
    managed_module_dir = pathlib.Path(__file__).parent.parent.joinpath("modules/managed").resolve()
    assert managed_module_dir.exists()
    assert managed_module_dir.is_dir()
    assert managed_module_dir.joinpath("main.tf").exists()
    assert managed_module_dir.joinpath("outputs.tf").exists()
    assert managed_module_dir.joinpath("variables.tf").exists()
    return managed_module_dir


@pytest.fixture(scope="session")
def root_fixture_dir(
    tmp_path_factory: pytest.TempPathFactory,
    backend_tf_builder: Callable[..., None],
    common_fixture_dir_ignores: Callable[[Any, list[str]], set[str]],
    root_module_dir: pathlib.Path,
) -> Callable[[str], pathlib.Path]:
    """Return a builder that makes a copy of the root module with backend configured appropriately."""

    def _builder(name: str) -> pathlib.Path:
        fixture_dir = tmp_path_factory.mktemp(name)
        shutil.copytree(
            src=root_module_dir,
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
def projects_client() -> resourcemanager_v3.ProjectsClient:
    """Return an initialized Resource Manager v3 Projects client."""
    return resourcemanager_v3.ProjectsClient()


@pytest.fixture(scope="session")
def project_details(
    project_id: str,
    projects_client: resourcemanager_v3.ProjectsClient,
) -> resourcemanager_v3.Project:
    """Return a Project object for the test session project_id."""
    result = projects_client.search_projects(
        request=resourcemanager_v3.SearchProjectsRequest(
            query=f"projectId:{project_id}",
        ),
    )
    return next(iter(result))


@pytest.fixture(scope="session")
def secret_manager_client() -> secretmanager_v1.SecretManagerServiceClient:
    """Return an initialized IAM Admin v1 client."""
    return secretmanager_v1.SecretManagerServiceClient()


@pytest.fixture(scope="session")
def list_global_secret_manager_secrets(
    project_id: str,
    secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
) -> Callable[[str], list[secretmanager_v1.Secret]]:
    """Return a function to list global Secret Manager Secrets with names that match the provided value."""

    def _lister(name: str) -> list[secretmanager_v1.Secret]:
        result = secret_manager_client.list_secrets(
            request=secretmanager_v1.ListSecretsRequest(
                parent=f"projects/{project_id}",
                filter=f"name:{name} ",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def region_secret_manager_client(region: str) -> secretmanager_v1.SecretManagerServiceClient:
    """Return an initialized IAM Admin v1 client."""
    return secretmanager_v1.SecretManagerServiceClient(
        client_options=client_options.ClientOptions(
            api_endpoint=f"secretmanager.{region}.rep.googleapis.com",
        ),
    )


@pytest.fixture(scope="session")
def list_regional_secret_manager_secrets(
    project_id: str,
    region: str,
    region_secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
) -> Callable[[str], list[secretmanager_v1.Secret]]:
    """Return a function to list regional Secret Manager Secrets with names that match the provided value."""

    def _lister(name: str) -> list[secretmanager_v1.Secret]:
        result = region_secret_manager_client.list_secrets(
            request=secretmanager_v1.ListSecretsRequest(
                parent=f"projects/{project_id}/locations/{region}",
                filter=f"name:{name}",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def secret_manager_secret_retriever(
    secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
    region_secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
) -> Callable[[str], secretmanager_v1.Secret]:
    """Return a retriever of Secret Manager Secrets by fully-qualified name."""

    def _retriever(name: str) -> secretmanager_v1.Secret:
        if re.search("/locations/", name):
            return region_secret_manager_client.get_secret(
                request=secretmanager_v1.GetSecretRequest(
                    name=name,
                ),
            )
        return secret_manager_client.get_secret(
            request=secretmanager_v1.GetSecretRequest(
                name=name,
            ),
        )

    return _retriever


@pytest.fixture(scope="module")
def secret_manager_secrets_from_output(
    secret_manager_secret_retriever: Callable[[str], secretmanager_v1.Secret],
) -> Callable[[dict[str, Any]], dict[str, dict[str, secretmanager_v1.Secret]]]:
    """Return a nested dict from the module output 'secret_ids', with common name as key and a dict of Secrets."""

    def _extractor(fixture_output: dict[str, Any]) -> dict[str, dict[str, secretmanager_v1.Secret]]:
        return {
            item[0]: {entry[0]: secret_manager_secret_retriever(entry[1]) for entry in item[1].items()}
            for item in cast("dict[str, dict[str, str]]", fixture_output.get("secret_ids", {})).items()
        }

    return _extractor


@pytest.fixture(scope="session")
def secret_manager_secret_version_is_enabled(
    secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
    region_secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
) -> Callable[[secretmanager_v1.Secret, str | None], bool]:
    """Return a function to lookup a Secret Manager Secret Version by name and version, returning True if Enabled."""

    def _is_enabled(secret: secretmanager_v1.Secret, version: str | None = None) -> bool:
        if not version:
            version = "latest"
        if re.search("/locations/", secret.name):
            secret_version = region_secret_manager_client.get_secret_version(
                request=secretmanager_v1.GetSecretVersionRequest(
                    name=f"{secret.name}/versions/{version}",
                ),
            )
        else:
            secret_version = secret_manager_client.get_secret_version(
                request=secretmanager_v1.GetSecretVersionRequest(
                    name=f"{secret.name}/versions/{version}",
                ),
            )
        assert secret_version
        return secret_version.state == secretmanager_v1.SecretVersion.State.ENABLED

    return _is_enabled


@pytest.fixture(scope="session")
def secret_manager_secret_version_payload_retriever(
    secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
    region_secret_manager_client: secretmanager_v1.SecretManagerServiceClient,
) -> Callable[[secretmanager_v1.Secret, str | None], bytes]:
    """Return a retriever of Secret Manager Secret Version payloads by fully-qualified name and version."""

    def _retriever(secret: secretmanager_v1.Secret, version: str | None = None) -> bytes:
        if not version:
            version = "latest"
        if re.search("/locations/", secret.name):
            content = region_secret_manager_client.access_secret_version(
                request=secretmanager_v1.AccessSecretVersionRequest(
                    name=f"{secret.name}/versions/{version}",
                ),
            )
        else:
            content = secret_manager_client.access_secret_version(
                request=secretmanager_v1.AccessSecretVersionRequest(
                    name=f"{secret.name}/versions/{version}",
                ),
            )
        assert content
        assert content.payload
        return content.payload.data

    return _retriever


@pytest.fixture(scope="session")
def certificate_manager_client() -> certificate_manager_v1.CertificateManagerClient:
    """Return an initialized Certificate Manager v1 client."""
    return certificate_manager_v1.CertificateManagerClient()


@pytest.fixture(scope="session")
def list_global_certificate_manager_certificates(
    project_id: str,
    certificate_manager_client: certificate_manager_v1.CertificateManagerClient,
) -> Callable[[str], list[certificate_manager_v1.Certificate]]:
    """Return a function to list global Certificate Manager Certificates with names that begin with the value."""

    def _lister(name: str) -> list[certificate_manager_v1.Certificate]:
        result = certificate_manager_client.list_certificates(
            request=certificate_manager_v1.ListCertificatesRequest(
                parent=f"projects/{project_id}/locations/global",
                filter=f"name:projects/{project_id}/locations/global/certificates/{name}",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def list_regional_certificate_manager_certificates(
    project_id: str,
    region: str,
    certificate_manager_client: certificate_manager_v1.CertificateManagerClient,
) -> Callable[[str], list[certificate_manager_v1.Certificate]]:
    """Return a function to list regional Certificate Manager Certificates with names that begin with the value."""

    def _lister(name: str) -> list[certificate_manager_v1.Certificate]:
        result = certificate_manager_client.list_certificates(
            request=certificate_manager_v1.ListCertificatesRequest(
                parent=f"projects/{project_id}/locations/{region}",
                filter=f"name:projects/{project_id}/locations/{region}/certificates/{name}",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def certificate_manager_certificate_retriever(
    certificate_manager_client: certificate_manager_v1.CertificateManagerClient,
) -> Callable[[str], certificate_manager_v1.Certificate]:
    """Return a function that can retrieve a Certificate Manager Certificate by fully-qualified name."""

    def _retriever(name: str) -> certificate_manager_v1.Certificate:
        certificate = certificate_manager_client.get_certificate(
            request=certificate_manager_v1.GetCertificateRequest(
                name=name,
            ),
        )
        assert certificate
        return certificate

    return _retriever


@pytest.fixture(scope="session")
def certificate_manager_certificates_from_output(
    certificate_manager_certificate_retriever: Callable[[str], certificate_manager_v1.Certificate],
) -> Callable[[dict[str, Any]], dict[str, certificate_manager_v1.Certificate]]:
    """Return a dict from module output 'certificate_manager_ids', with common name as key and Certificate as value."""

    def _extractor(fixture_output: dict[str, Any]) -> dict[str, certificate_manager_v1.Certificate]:
        return {
            item[0]: certificate_manager_certificate_retriever(item[1])
            for item in cast("dict[str, str]", fixture_output.get("certificate_manager_ids", {})).items()
        }

    return _extractor


@pytest.fixture(scope="session")
def ssl_certificates_client() -> compute_v1.SslCertificatesClient:
    """Return an initialized Compute Engine v1 global SSL Certificates client."""
    return compute_v1.SslCertificatesClient()


@pytest.fixture(scope="session")
def list_global_ssl_certificates(
    project_id: str,
    ssl_certificates_client: compute_v1.SslCertificatesClient,
) -> Callable[[str], list[compute_v1.SslCertificate]]:
    """Return a function to list global Compute Engine SSL Certificates with names that begin with provided value."""

    def _lister(name: str) -> list[compute_v1.SslCertificate]:
        result = ssl_certificates_client.list(
            request=compute_v1.ListSslCertificatesRequest(
                project=project_id,
                filter=f"name eq {name}.*",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def region_ssl_certificates_client() -> compute_v1.RegionSslCertificatesClient:
    """Return an initialized Compute Engine v1 regional SSL Certificates client."""
    return compute_v1.RegionSslCertificatesClient()


@pytest.fixture(scope="session")
def list_regional_ssl_certificates(
    project_id: str,
    region: str,
    region_ssl_certificates_client: compute_v1.RegionSslCertificatesClient,
) -> Callable[[str], list[compute_v1.SslCertificate]]:
    """Return a function to list regional Compute Engine SSL Certificates with names that begin with provided value."""

    def _lister(name: str) -> list[compute_v1.SslCertificate]:
        result = region_ssl_certificates_client.list(
            request=compute_v1.ListRegionSslCertificatesRequest(
                project=project_id,
                region=region,
                filter=f"name eq {name}.*",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def ssl_certificate_retriever(
    ssl_certificates_client: compute_v1.SslCertificatesClient,
    region_ssl_certificates_client: compute_v1.RegionSslCertificatesClient,
) -> Callable[[str], compute_v1.SslCertificate]:
    """Return a function that can retrieve a regional or global Compute Engine SslCertificate by name."""

    def _global(project: str, name: str) -> compute_v1.SslCertificate:
        return ssl_certificates_client.get(
            request=compute_v1.GetSslCertificateRequest(
                project=project,
                ssl_certificate=name,
            ),
        )

    def _regional(project: str, region: str, name: str) -> compute_v1.SslCertificate:
        return region_ssl_certificates_client.get(
            request=compute_v1.GetRegionSslCertificateRequest(
                project=project,
                region=region,
                ssl_certificate=name,
            ),
        )

    def _retriever(name: str) -> compute_v1.SslCertificate:
        match = re.search(REGIONAL_SSL_CERTIFICATE_SELF_LINK_PATTERN, name)
        if match:
            project, region, cert_name = match.groups()
            certificate = _regional(project=project, region=region, name=cert_name)
        else:
            match = re.search(GLOBAL_SSL_CERTIFICATE_SELF_LINK_PATTERN, name)
            if match:
                project, cert_name = match.groups()
                certificate = _global(project=project, name=cert_name)
            else:
                raise ValueError(f"Compute Engine SSL certificate name '{name}' is invalid")  # noqa: EM102, TRY003
        assert certificate
        return certificate

    return _retriever


@pytest.fixture(scope="session")
def ssl_certificates_from_output(
    ssl_certificate_retriever: Callable[[str], compute_v1.SslCertificate],
) -> Callable[[dict[str, Any]], dict[str, compute_v1.SslCertificate]]:
    """Return a dict from output 'ssl_certificate_self_links', with common name as key and SslCertificate as value."""

    def _extractor(fixture_output: dict[str, Any]) -> dict[str, compute_v1.SslCertificate]:
        return {
            item[0]: ssl_certificate_retriever(item[1])
            for item in cast("dict[str, str]", fixture_output.get("ssl_certificate_self_links", {})).items()
        }

    return _extractor


@pytest.fixture(scope="session")
def iam_admin_client() -> iam_admin_v1.IAMClient:
    """Return an initialized IAM Admin v1 client."""
    return iam_admin_v1.IAMClient()


@pytest.fixture(scope="session")
def service_account_builder(
    request: pytest.FixtureRequest,
    project_id: str,
    iam_admin_client: iam_admin_v1.IAMClient,
) -> Callable[[str, str, str], str]:
    """Return a builder of service accounts."""

    def _builder(
        name: str,
        display_name: str | None = None,
        description: str | None = None,
    ) -> str:
        """Create a service account with given name, returning it's email address, with automatic deletion after use."""
        if display_name is None:
            display_name = "terraform-google-tls-certificate test account"
        if description is None:
            description = "A test service account for automated TLS testing."

        def _cleanup() -> None:
            if not skip_destroy_phase():
                iam_admin_client.delete_service_account(
                    request=iam_admin_v1.DeleteServiceAccountRequest(
                        name=sa.name,
                    ),
                )

        try:
            sa_accounts = iam_admin_client.list_service_accounts(
                name=f"projects/{project_id}",
            )
            sa = next(sa for sa in sa_accounts if re.search(f"serviceAccounts/{name}", sa.name))
        except (StopIteration, exceptions.NotFound):
            sa = iam_admin_client.create_service_account(
                request=iam_admin_v1.CreateServiceAccountRequest(
                    account_id=name,
                    name=f"projects/{project_id}",
                    service_account=iam_admin_v1.ServiceAccount(
                        display_name=display_name,
                        description=description,
                    ),
                ),
            )
        request.addfinalizer(_cleanup)
        return sa.email

    return _builder


@pytest.fixture(scope="session")
def ssl_policies_client() -> compute_v1.SslPoliciesClient:
    """Return an initialized Compute Engine v1 global SSL Policies client."""
    return compute_v1.SslPoliciesClient()


@pytest.fixture(scope="session")
def list_global_ssl_policies(
    project_id: str,
    ssl_policies_client: compute_v1.SslPoliciesClient,
) -> Callable[[str], list[compute_v1.SslPolicy]]:
    """Return a function to list global Compute Engine SSL Policies with names that begin with provided value."""

    def _lister(name: str) -> list[compute_v1.SslPolicy]:
        result = ssl_policies_client.list(
            request=compute_v1.ListSslPoliciesRequest(
                project=project_id,
                filter=f"name eq {name}.*",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def region_ssl_policies_client() -> compute_v1.RegionSslPoliciesClient:
    """Return an initialized Compute Engine v1 regional SSL Policies client."""
    return compute_v1.RegionSslPoliciesClient()


@pytest.fixture(scope="session")
def list_regional_ssl_policies(
    project_id: str,
    region: str,
    region_ssl_policies_client: compute_v1.RegionSslPoliciesClient,
) -> Callable[[str], list[compute_v1.SslPolicy]]:
    """Return a function to list regional Compute Engine SSL Policies with names that begin with provided value."""

    def _lister(name: str) -> list[compute_v1.SslPolicy]:
        result = region_ssl_policies_client.list(
            request=compute_v1.ListRegionSslPoliciesRequest(
                project=project_id,
                region=region,
                filter=f"name eq {name}.*",
            ),
        )
        assert result is not None
        return list(result)

    return _lister


@pytest.fixture(scope="session")
def ssl_policy_retriever(
    ssl_policies_client: compute_v1.SslPoliciesClient,
    region_ssl_policies_client: compute_v1.RegionSslPoliciesClient,
) -> Callable[[str], compute_v1.SslPolicy]:
    """Return a function that can retrieve a regional or global Compute Engine SslPolicy by name."""

    def _global(project: str, name: str) -> compute_v1.SslPolicy:
        return ssl_policies_client.get(
            request=compute_v1.GetSslPolicyRequest(
                project=project,
                ssl_policy=name,
            ),
        )

    def _regional(project: str, region: str, name: str) -> compute_v1.SslPolicy:
        return region_ssl_policies_client.get(
            request=compute_v1.GetRegionSslPolicyRequest(
                project=project,
                region=region,
                ssl_policy=name,
            ),
        )

    def _retriever(name: str) -> compute_v1.SslPolicy:
        match = re.search(REGIONAL_SSL_POLICY_SELF_LINK_PATTERN, name)
        if match:
            project, region, policy_name = match.groups()
            certificate = _regional(project=project, region=region, name=policy_name)
        else:
            match = re.search(GLOBAL_SSL_POLICY_SELF_LINK_PATTERN, name)
            if match:
                project, policy_name = match.groups()
                certificate = _global(project=project, name=policy_name)
            else:
                raise ValueError(f"Compute Engine SSL policy name '{name}' is invalid")  # noqa: EM102, TRY003
        assert certificate
        return certificate

    return _retriever


@pytest.fixture(scope="session")
def ssl_policy_from_output(
    ssl_policy_retriever: Callable[[str], compute_v1.SslPolicy],
) -> Callable[[dict[str, Any]], compute_v1.SslPolicy | None]:
    """Return a SslPolicy from output 'ssl_policy_self_link', or None."""

    def _extractor(fixture_output: dict[str, Any]) -> compute_v1.SslPolicy | None:
        self_link = fixture_output.get("ssl_policy_self_link")
        if not self_link:
            return None
        return ssl_policy_retriever(self_link)

    return _extractor
