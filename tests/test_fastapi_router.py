"""Tests for OntoRouter CRUD routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from ontosql.fastapi.deps import onto_session_lifespan
from ontosql.fastapi.router import OntoRouter
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow

pytest.importorskip("fastapi")


@pytest.fixture
def api_client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()

    app = FastAPI()
    onto_session_lifespan(app, engine, [PersonMap, OrganizationMap])
    router = OntoRouter(maps=[PersonMap, OrganizationMap])
    router.register(Person)
    router.register(Organization)
    router.include_in(app)

    return TestClient(app)


def test_get_person(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person/1")
    assert resp.status_code == 200
    assert "Ada Lovelace" in resp.text


def test_list_persons(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_and_delete_person(api_client: TestClient) -> None:
    create = api_client.post("/onto/person", json={"name": "Grace Hopper", "employer": None})
    assert create.status_code == 201
    assert "Grace Hopper" in create.text
    new_id = int(create.json()["@id"].split("/")[-1])

    patch = api_client.patch(f"/onto/person/{new_id}", json={"name": "Grace M. Hopper"})
    assert patch.status_code == 200
    assert "Grace M. Hopper" in patch.text

    delete = api_client.delete(f"/onto/person/{new_id}")
    assert delete.status_code == 204
    assert api_client.get(f"/onto/person/{new_id}").status_code == 404
