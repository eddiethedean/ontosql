"""Tests for OntoRouter CRUD routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ontosql.fastapi.router import OntoRouter
from tests.models import OrganizationMap, Person, PersonMap

pytest.importorskip("fastapi")


@pytest.fixture
def api_client(api_client_full: TestClient) -> TestClient:
    return api_client_full


def _person_name_from_graph(body: dict) -> str:
    for node in body["@graph"]:
        name = node.get("https://schema.org/name")
        if name and node["@id"].endswith("/person/"):
            return name[0]["@value"]
    for node in body["@graph"]:
        name = node.get("https://schema.org/name")
        if name and "/person/" in node["@id"]:
            return name[0]["@value"]
    raise AssertionError(f"No person name in graph: {body}")


def test_get_person_jsonld(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person/1", headers={"Accept": "application/ld+json"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/ld+json")
    body = resp.json()
    assert "@graph" in body
    assert _person_name_from_graph(body) == "Ada Lovelace"


def test_get_person_turtle(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person/1", headers={"Accept": "text/turtle"})
    assert resp.status_code == 200
    assert "text/turtle" in resp.headers["content-type"]
    assert "Ada Lovelace" in resp.text
    assert "schema:Person" in resp.text or "https://schema.org/Person" in resp.text


def test_get_person_ntriples(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person/1", headers={"Accept": "application/n-triples"})
    assert resp.status_code == 200
    assert "n-triples" in resp.headers["content-type"]
    assert "Ada Lovelace" in resp.text


def test_list_persons_json(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Ada Lovelace"


def test_list_persons_jsonld_document_shape(api_client: TestClient) -> None:
    """List JSON-LD must be one document with @context + flat @graph nodes."""
    resp = api_client.get("/onto/person", headers={"Accept": "application/ld+json"})
    assert resp.status_code == 200
    body = resp.json()
    assert "@context" in body
    assert "@graph" in body
    assert isinstance(body["@graph"], list)
    assert len(body["@graph"]) >= 1
    for node in body["@graph"]:
        assert isinstance(node, dict)
        assert "@id" in node
        assert "@context" not in node, "list nodes must not nest full JSON-LD documents"


def test_create_and_delete_person(api_client: TestClient) -> None:
    create = api_client.post("/onto/person", json={"name": "Grace Hopper", "employer": None})
    assert create.status_code == 201
    create_body = create.json()
    new_id = int(create_body["@id"].split("/")[-1])
    assert create_body["https://schema.org/name"][0]["@value"] == "Grace Hopper"

    patch = api_client.patch(f"/onto/person/{new_id}", json={"name": "Grace M. Hopper"})
    assert patch.status_code == 200
    patch_body = patch.json()
    assert patch_body["https://schema.org/name"][0]["@value"] == "Grace M. Hopper"

    delete = api_client.delete(f"/onto/person/{new_id}")
    assert delete.status_code == 204
    assert api_client.get(f"/onto/person/{new_id}").status_code == 404


def test_patch_not_found(api_client: TestClient) -> None:
    assert api_client.patch("/onto/person/999", json={"name": "X"}).status_code == 404


def test_router_skip_duplicate_register() -> None:
    router = OntoRouter(maps=[PersonMap, OrganizationMap])
    router.register(Person)
    router.register(Person)
    assert len(router._entities) == 1


def test_list_pagination_params(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person?limit=1&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_limit_capped_at_100(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person?limit=101")
    assert resp.status_code == 422
