"""Tests for RDF format helpers."""

from __future__ import annotations

import pytest

from ontosql.rdf.formats import media_type_for_format, normalize_format


def test_normalize_format_aliases() -> None:
    assert normalize_format("ttl") == "turtle"
    assert normalize_format("jsonld") == "json-ld"


def test_media_type_for_format() -> None:
    assert media_type_for_format("turtle") == "text/turtle"


def test_normalize_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        normalize_format("not-a-format")
