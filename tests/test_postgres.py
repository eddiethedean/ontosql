"""Postgres integration smoke tests (skipped unless ONTO_TEST_DATABASE_URL is set)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from ontosql import OntoSession
from tests.models import OrganizationMap, OrgRow, Person, PersonMap, PersonRow

DATABASE_URL = os.environ.get("ONTO_TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="Set ONTO_TEST_DATABASE_URL for Postgres integration tests",
)


@pytest.fixture
def postgres_engine():
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(OrgRow(id=10, name="Postgres Org"))
        session.add(PersonRow(id=1, name="Postgres Ada", org_id=10))
        session.commit()
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_postgres_session_get_and_find(postgres_engine) -> None:
    with OntoSession(postgres_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = session.get(Person, id=1)
        assert person is not None
        assert person.name == "Postgres Ada"
        assert person.employer is not None
        assert person.employer.name == "Postgres Org"

        results = session.find(Person, where=Person.name.startswith("Postgres"))
        assert len(results) == 1


def test_postgres_session_save_round_trip(postgres_engine) -> None:
    with OntoSession(postgres_engine, maps=[PersonMap, OrganizationMap]) as session:
        session.save(Person(id=2, name="New Person", employer=None))
    with OntoSession(postgres_engine, maps=[PersonMap, OrganizationMap]) as session:
        loaded = session.get(Person, id=2)
        assert loaded is not None
        assert loaded.name == "New Person"
