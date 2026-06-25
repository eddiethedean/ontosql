"""Tests for graph materialization."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from ontosql.sync.materialize import materialize_entity, materialize_find
from tests.models import Organization, OrganizationMap, Person, PersonMap


@pytest.fixture
def session(sync_engine):
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as s:
        yield s


def test_materialize_entity() -> None:
    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=10, name="Acme"),
    )
    graph = materialize_entity(person)
    assert len(graph) > 0


def test_materialize_find(session) -> None:
    graph = materialize_find(session, Person, limit=2)
    assert len(graph) > 0
