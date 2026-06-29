"""Integration tests for synchronous OntoSession."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from tests.models import Person


def test_get_by_id(onto_session) -> None:
    person = onto_session.get(Person, identity=1)
    assert person is not None
    assert person.name == "Ada Lovelace"
    assert person.employer is not None
    assert person.employer.name == "Analytical Engines Inc."


def test_get_by_iri(onto_session) -> None:
    person = onto_session.get(Person, iri="https://data.example.org/person/1")
    assert person is not None
    assert person.id == 1


def test_get_missing(onto_session) -> None:
    assert onto_session.get(Person, identity=999) is None


def test_get_requires_id_or_iri(onto_session) -> None:
    with pytest.raises(ValueError, match="requires identity="):
        onto_session.get(Person)


def test_find_with_filter(onto_session) -> None:
    results = onto_session.find(Person, where=Person.name.startswith("A"))
    assert len(results) == 1
    assert results[0].name == "Ada Lovelace"


def test_find_limit(onto_session) -> None:
    results = onto_session.find(Person, limit=2)
    assert len(results) == 2


def test_find_no_employer(onto_session) -> None:
    results = onto_session.find(Person, where=Person.name == "Solo Person")
    assert len(results) == 1
    assert results[0].employer is None


def test_unregistered_entity(sync_engine) -> None:
    with (
        OntoSession(sync_engine, maps=[]) as session,
        pytest.raises(KeyError, match="No mapper registered"),
    ):
        session.get(Person, identity=1)
