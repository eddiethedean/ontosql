"""Tests for optional JSON-LD extra."""

from __future__ import annotations

import pytest

pytest.importorskip("pyld")

from ontosql.export import jsonld as jsonld_module
from ontosql.export.jsonld import compact_jsonld, frame_jsonld


def test_compact_jsonld() -> None:
    doc = {"@id": "http://ex/a", "http://schema.org/name": "Ada"}
    ctx = {"schema": "http://schema.org/"}
    out = compact_jsonld(doc, ctx)
    assert "schema:name" in out or "@graph" in out


def test_frame_jsonld() -> None:
    doc = {
        "@context": {"schema": "http://schema.org/"},
        "@graph": [{"@id": "http://ex/a", "@type": "schema:Person", "schema:name": "Ada"}],
    }
    frame = {"@type": "schema:Person"}
    out = frame_jsonld(doc, frame)
    assert out is not None


def test_jsonld_import_error() -> None:
    import sys
    from unittest.mock import patch

    with (
        patch.dict(sys.modules, {"pyld": None, "pyld.jsonld": None}),
        pytest.raises(ImportError, match="jsonld"),
    ):
        jsonld_module._require_pyld()
