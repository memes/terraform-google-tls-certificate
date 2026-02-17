"""Define functions common to all test cases in the tests namespace."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from google.cloud import certificate_manager_v1

type AsserterFunc = Callable[[str | bytes | None], None]

DEFAULT_CA_CNAME = "Testing CA"


def skip_destroy_phase() -> bool:
    """Determine if resource destroy phase should be skipped for successful fixtures."""
    return os.getenv("TEST_SKIP_DESTROY_PHASE", "False").lower() in ["true", "t", "yes", "y", "1"]


def get_tf_command() -> str:
    """Return an explicit command to use for module execution or the first tofu or terraform binary found in PATH.

    NOTE: Preference will be given to the value of environment variable TEST_TF_COMMAND.
    """
    tf_command = os.getenv("TEST_TF_COMMAND") or shutil.which("tofu") or shutil.which("terraform")
    assert tf_command, "A tofu or terraform binary could not be determined"
    return tf_command


@contextmanager
def run_tf_plan_apply_destroy(
    fixture: pathlib.Path,
    tfvars: dict[str, Any] | None,
    workspace: str | None = None,
    tf_command: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Execute terraform/tofu fixture lifecycle in an optional workspace, yielding the output post-apply.

    NOTE: Resources will not be destroyed if the test case raises an error.
    """
    if tfvars is None:
        tfvars = {}
    if not tf_command:
        tf_command = get_tf_command()
    if workspace is not None and workspace != "":
        subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "workspace",
                "select",
                "-or-create",
                workspace,
            ],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [
            tf_command,
            f"-chdir={fixture!s}",
            "init",
            "-no-color",
            "-input=false",
        ],
        check=True,
        capture_output=True,
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="tfvars",
        suffix=".json",
        encoding="utf-8",
        delete_on_close=False,
        delete=True,
    ) as tfvar_file:
        json.dump(tfvars, tfvar_file, ensure_ascii=False, indent=2)
        tfvar_file.close()
        # Validate module
        subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "validate",
                "-no-color",
                f"-var-file={tfvar_file.name}",
            ],
            check=True,
            capture_output=True,
        )
        # Execute plan then apply with a common plan file.
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix="tf",
            suffix=".plan",
            delete_on_close=False,
            delete=True,
        ) as plan_file:
            plan_file.close()
            subprocess.run(
                [
                    tf_command,
                    f"-chdir={fixture!s}",
                    "plan",
                    "-no-color",
                    "-input=false",
                    f"-var-file={tfvar_file.name}",
                    f"-out={plan_file.name}",
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    tf_command,
                    f"-chdir={fixture!s}",
                    "apply",
                    "-no-color",
                    "-input=false",
                    "-auto-approve",
                    plan_file.name,
                ],
                check=True,
                capture_output=True,
            )

        # Run plan again with -detailed-exitcode flag, which will only return an exit code of 0 if there are no further
        # changes. This is to find subtle issues in the Terraform declaration which inadvertently triggers unexpected
        # resource updates or recreations.
        subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "plan",
                "-no-color",
                "-input=false",
                "-detailed-exitcode",
                f"-var-file={tfvar_file.name}",
            ],
            check=True,
            capture_output=True,
        )
        output = subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "output",
                "-no-color",
                "-json",
            ],
            check=True,
            capture_output=True,
        )
        try:
            yield {k: v["value"] for k, v in json.loads(output.stdout).items()}
            if not skip_destroy_phase():
                subprocess.run(
                    [
                        tf_command,
                        f"-chdir={fixture!s}",
                        "destroy",
                        "-no-color",
                        "-input=false",
                        "-auto-approve",
                        f"-var-file={tfvar_file.name}",
                    ],
                    check=True,
                    capture_output=True,
                )
        finally:
            subprocess.run(
                [
                    tf_command,
                    f"-chdir={fixture!s}",
                    "workspace",
                    "select",
                    "default",
                ],
                check=True,
                capture_output=True,
            )


@contextmanager
def run_tf_test(
    fixture: pathlib.Path,
    tfvars: dict[str, Any] | None = None,
    workspace: str | None = None,
    tf_command: str | None = None,
) -> Generator[list[dict[str, Any]], None, None]:
    """Execute terraform/tofu test lifecycle in an optional workspace, yielding the output as a JSON array."""
    if tfvars is None:
        tfvars = {}
    if not tf_command:
        tf_command = get_tf_command()
    if workspace is not None and workspace != "":
        subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "workspace",
                "select",
                "-or-create",
                workspace,
            ],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [
            tf_command,
            f"-chdir={fixture!s}",
            "init",
            "-no-color",
            "-input=false",
        ],
        check=True,
        capture_output=True,
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="tfvars",
        suffix=".json",
        encoding="utf-8",
        delete_on_close=False,
        delete=True,
    ) as tfvar_file:
        json.dump(tfvars, tfvar_file, ensure_ascii=False, indent=2)
        tfvar_file.close()
        output = subprocess.run(
            [
                tf_command,
                f"-chdir={fixture!s}",
                "test",
                "-json",
                f"-var-file={tfvar_file.name}",
            ],
            check=False,
            capture_output=True,
        )
        yield [json.loads(line) for line in output.stdout.splitlines()]


def certificate_from_data(data: str | bytes) -> x509.Certificate:
    """Return an x509 Certificate object built from the PEM string or bytes, or None."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return x509.load_pem_x509_certificate(data=data)


def certificates_from_output(fixture_output: dict[str, Any]) -> dict[str, x509.Certificate]:
    """Return a dict from the module output 'certificates', with common name as key and Certificate as value."""
    return {
        item[0]: certificate_from_data(item[1])
        for item in cast("dict[str, str]", fixture_output.get("certificates", {})).items()
    }


def re_asserter_builder(pattern: str | re.Pattern[str]) -> AsserterFunc:
    """Build an asserter for supplied regex."""
    if isinstance(pattern, str):
        pattern = re.compile(pattern)

    def _asserter(value: str | bytes | None) -> None:
        """Raise an AssertionError if value does not match regex."""
        assert value is not None
        if isinstance(value, bytes):
            value = value.decode(encoding="utf-8")
        assert re.search(pattern=pattern, string=value)

    return _asserter


def equal_asserter_builder(expected: str | bytes | None) -> AsserterFunc:
    """Return a function that can test the supplied value is equal to expected value."""

    def _asserter(value: str | bytes | None) -> None:
        """Raise an AssertionError if the value does not meet expectations."""
        assert value == expected

    return _asserter


def unset_asserter(value: str | bytes | None) -> None:
    """Raise an AssertionError if the value is anything other than falsy."""
    assert not value


def has_value_asserter(value: str | bytes | None) -> None:
    """Raise an AssertionError if value is empty."""
    assert value
    assert len(value) > 0


def assert_default_ca_cert(
    ca_cert: x509.Certificate | None,
    cname_asserter: AsserterFunc | None = None,
) -> None:
    """Raise an AssertionError if the Certificate object does not meet expectations for default CA certificate."""
    if cname_asserter is None:
        cname_asserter = equal_asserter_builder(DEFAULT_CA_CNAME)
    assert ca_cert
    assert ca_cert.not_valid_before_utc < datetime.now(UTC)
    assert ca_cert.not_valid_after_utc > datetime.now(UTC)
    assert isinstance(ca_cert.public_key(), ec.EllipticCurvePublicKey)
    assert isinstance(cast("ec.EllipticCurvePublicKey", ca_cert.public_key()).curve, ec.SECP256R1)
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


def assert_default_cert(
    cert: x509.Certificate | None,
    cname_asserter: AsserterFunc | None = None,
) -> None:
    """Raise an AssertionError if the Certificate object does not meet expectations for default TLS certificate."""
    if cname_asserter is None:
        cname_asserter = has_value_asserter
    assert cert
    assert cert.not_valid_before_utc < datetime.now(UTC)
    assert cert.not_valid_after_utc > datetime.now(UTC)
    assert isinstance(cert.public_key(), ec.EllipticCurvePublicKey)
    assert isinstance(cast("ec.EllipticCurvePublicKey", cert.public_key()).curve, ec.SECP256R1)
    assert cert.subject
    cname = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    assert len(cname) == 1
    cname_asserter(cname[0].value)
    assert cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATION_NAME, value="F5, Inc"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATIONAL_UNIT_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.ORGANIZATIONAL_UNIT_NAME, value="F5 DevCentral Demos"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.LOCALITY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.LOCALITY_NAME, value="Seattle"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.STATE_OR_PROVINCE_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.STATE_OR_PROVINCE_NAME, value="Washington"),
    ]
    assert cert.subject.get_attributes_for_oid(x509.NameOID.COUNTRY_NAME) == [
        x509.NameAttribute(oid=x509.NameOID.COUNTRY_NAME, value="US"),
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
        ],
    )


def default_assert_key(key: Any) -> None:  # noqa: ANN401
    """Raise an AssertionError if the private key does not match expectations."""
    assert key is not None
    assert isinstance(key.curve, ec.SECP256R1)


def default_assert_certificate_manager_certificate(
    cert: certificate_manager_v1.Certificate,
    description_asserter: AsserterFunc | None = None,
    expected_labels: dict[str, str] | None = None,
    cname_asserter: AsserterFunc | None = None,
    ca_cname_asserter: AsserterFunc | None = None,
) -> None:
    """Raise an AssertionError if the Certificate Manager Certificate does not match expectations."""
    if description_asserter is None:
        description_asserter = unset_asserter
    assert cert
    description_asserter(cert.description)
    assert cert.labels is not None
    if expected_labels is not None:
        assert all(item in cert.labels.items() for item in expected_labels.items())
    assert cert.self_managed is not None
    assert not cert.managed
    assert cert.pem_certificate
    certs_in_chain = x509.load_pem_x509_certificates(cert.pem_certificate.encode(encoding="utf-8"))
    assert len(certs_in_chain) == 2  # noqa: PLR2004
    assert_default_cert(cert=certs_in_chain[0], cname_asserter=cname_asserter)
    assert_default_ca_cert(certs_in_chain[1], cname_asserter=ca_cname_asserter)
    assert cert.scope == certificate_manager_v1.Certificate.Scope.ALL_REGIONS
