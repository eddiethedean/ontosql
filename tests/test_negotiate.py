"""Tests for Accept header negotiation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from ontosql.fastapi.negotiate import _parse_accept, negotiate_onto_response

pytest.importorskip("fastapi")

TURTLE_SAMPLE = (
    '@prefix schema: <https://schema.org/> .\n<http://example.org/person/1> schema:name "Ada" .\n'
)


def test_parse_accept_json_vs_ldjson_q_values() -> None:
    assert (
        _parse_accept("application/json;q=0.1, application/ld+json;q=0.9") == "application/ld+json"
    )
    assert _parse_accept("application/json;q=0.9, application/ld+json;q=0.1") == "application/json"


def test_parse_accept_empty() -> None:
    assert _parse_accept(None) is None
    assert _parse_accept("") is None


def test_parse_accept_turtle() -> None:
    assert _parse_accept("text/turtle, application/ld+json;q=0.8") == "text/turtle"


def test_parse_accept_charset() -> None:
    assert _parse_accept("text/turtle; charset=utf-8") == "text/turtle"
    assert _parse_accept("application/ld+json; charset=utf-8") == "application/ld+json"


def test_parse_accept_q_zero_rejected() -> None:
    assert _parse_accept("text/turtle;q=0") is None


def test_parse_accept_q_with_charset() -> None:
    assert (
        _parse_accept("application/ld+json;q=0.9; charset=utf-8, text/turtle;q=1") == "text/turtle"
    )


def test_parse_accept_wildcard_returns_none() -> None:
    assert _parse_accept("*/*") is None
    assert _parse_accept("application/*") is None


def test_parse_accept_no_substring_match() -> None:
    assert _parse_accept("text") is None
    assert _parse_accept("json") is None


def test_negotiate_plain_dict() -> None:
    request = MagicMock()
    request.headers.get.return_value = None
    doc = {"@context": {}, "@id": "http://example.org/x"}
    resp = negotiate_onto_response(request, doc)
    assert resp.media_type == "application/ld+json"


def test_negotiate_turtle_string() -> None:
    request = MagicMock()
    request.headers.get.return_value = "text/turtle"
    resp = negotiate_onto_response(request, TURTLE_SAMPLE)
    assert resp.media_type == "text/turtle"
    assert "schema:name" in resp.body.decode()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.get("/person/{person_id}")
    def get_person(person_id: int, request: Request) -> object:
        if "turtle" in (request.headers.get("accept") or "").lower():
            return negotiate_onto_response(request, TURTLE_SAMPLE)
        doc = {
            "@context": {"schema": "https://schema.org/"},
            "@id": f"http://example.org/person/{person_id}",
            "schema:name": "Ada Lovelace",
        }
        return negotiate_onto_response(request, doc)

    return TestClient(app)


def test_client_turtle_with_charset(client: TestClient) -> None:
    r = client.get("/person/1", headers={"Accept": "text/turtle; charset=utf-8"})
    assert r.status_code == 200
    assert "text/turtle" in r.headers["content-type"]
    assert "schema:name" in r.text


def test_client_ld_json_lower_q_than_turtle(client: TestClient) -> None:
    r = client.get(
        "/person/1",
        headers={"Accept": "application/ld+json;q=0.5, text/turtle;q=1"},
    )
    assert r.status_code == 200
    assert "text/turtle" in r.headers["content-type"]
