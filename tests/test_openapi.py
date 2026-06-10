"""Tests for FastAPI OpenAPI enrichment."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from ontosql.fastapi.openapi import enrich_openapi_schema, install_onto_openapi
from tests.models import Person

pytest.importorskip("fastapi")


def test_openapi_enrichment() -> None:
    app = FastAPI(title="Onto", version="0.3.1")
    schema = enrich_openapi_schema(app, [Person])
    assert "Person" in schema["components"]["schemas"]
    assert schema["components"]["schemas"]["Person"]["x-ontosql-type-iri"]
    install_onto_openapi(app, [Person])
    assert app.openapi()["components"]["schemas"]["Person"]["x-ontosql-type-iri"]


def test_openapi_cached_schema() -> None:
    app = FastAPI(title="Onto", version="0.3.1")
    install_onto_openapi(app, [Person])
    first = app.openapi()
    second = app.openapi()
    assert first is second


def test_openapi_without_type_iri() -> None:
    class NoIri:
        __name__ = "NoIri"
        jsonld_context = {"ex": "http://example.org/"}

    app = FastAPI()
    schema = enrich_openapi_schema(app, [NoIri])  # type: ignore[list-item]
    assert "x-ontosql-context" in schema["components"]["schemas"]["NoIri"]
    assert "x-ontosql-type-iri" not in schema["components"]["schemas"]["NoIri"]


def test_openapi_existing_component() -> None:
    app = FastAPI()

    class Existing:
        __name__ = "Existing"
        type_iri = "schema:Person"
        jsonld_context = {"schema": "https://schema.org/"}

    with patch("ontosql.fastapi.openapi.get_openapi") as mock_openapi:
        mock_openapi.return_value = {
            "components": {"schemas": {"Existing": {"type": "object"}}},
        }
        schema = enrich_openapi_schema(app, [Existing])  # type: ignore[list-item]
        assert schema["components"]["schemas"]["Existing"]["x-ontosql-context"]
