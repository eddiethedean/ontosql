"""FastAPI response serialization branches."""

from __future__ import annotations

import pytest

from ontosql.fastapi.responses import _serialize_data

pytest.importorskip("fastapi")


@pytest.mark.parametrize(
    ("data", "expected_in_body"),
    [
        ({"@id": "http://ex/x", "@type": "Thing"}, "http://ex/x"),
        ('{"@id": "http://ex/z"}', "http://ex/z"),
    ],
)
def test_serialize_jsonld_payload(data: object, expected_in_body: str) -> None:
    body, mt = _serialize_data(data, "json-ld")
    assert mt == "application/ld+json"
    assert expected_in_body in body


def test_serialize_jsonld_non_callable_to_jsonld() -> None:
    class Broken:
        to_jsonld = 1

    with pytest.raises(TypeError, match="to_jsonld/to_rdf"):
        _serialize_data(Broken(), "json-ld")


def test_serialize_jsonld_callable() -> None:
    class WithJsonLd:
        def to_jsonld(self) -> dict:
            return {"@id": "http://ex/y", "name": "Test"}

    body, mt = _serialize_data(WithJsonLd(), "json-ld")
    assert mt == "application/ld+json"
    assert "http://ex/y" in body
    assert "Test" in body
