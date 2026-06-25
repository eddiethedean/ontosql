"""Tests for curated prefix bundles."""

from __future__ import annotations

import pytest

from ontosql.registry import CURATED_PREFIXES, PrefixRegistry


def test_curated_schema_org() -> None:
    reg = PrefixRegistry.curated("schema_org")
    assert reg.expand("schema:Person") == "https://schema.org/Person"


def test_curated_dcterms() -> None:
    reg = PrefixRegistry.curated("dcterms")
    assert reg.expand("dcterms:title").startswith("http://purl.org/dc/terms/")


def test_curated_unknown_bundle() -> None:
    with pytest.raises(KeyError, match="Unknown prefix bundle"):
        PrefixRegistry.curated("unknown")


def test_curated_extra_prefix() -> None:
    reg = PrefixRegistry.curated("schema_org", extra={"ex": "https://example.org/"})
    assert reg.expand("ex:Thing") == "https://example.org/Thing"


def test_curated_prefixes_defined() -> None:
    assert "schema_org" in CURATED_PREFIXES
    assert "dcterms" in CURATED_PREFIXES
