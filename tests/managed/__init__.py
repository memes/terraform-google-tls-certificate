"""Define functions common to all test cases in the managed namespace."""

from typing import cast

from google.cloud import dns


def assert_managed_zone(managed_zone: dns.zone.ManagedZone, expected_domain: str) -> None:
    """Raise an AssertionError if the Cloud DNS Managed Zone does not meet expectations."""
    if not expected_domain.endswith("."):
        expected_domain = f"{expected_domain}."
    managed_zone.reload()
    assert managed_zone.dns_name == expected_domain
    for rr in [
        cast("dns.resource_record_set.ResourceRecordSet", rr)
        for rr in managed_zone.list_resource_record_sets()
        if rr.record_type not in ["NS", "SOA"]
    ]:
        assert rr.record_type == "CNAME"
        assert rr.name.startswith("_acme-challenge")
        assert len(rr.rrdatas) == 1
        for rrdata in rr.rrdatas:
            assert rrdata.endswith("certificatemanager.goog.")
