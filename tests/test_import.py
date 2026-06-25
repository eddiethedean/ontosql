"""Tests for RDF import."""

from __future__ import annotations

import pytest

from ontosql.import_ import OntoImportError, import_from_jsonld, import_from_rdf
from tests.models import Organization, Person, PersonMap


def test_jsonld_round_trip() -> None:
    person = Person(
        id=1,
        name="Ada Lovelace",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    doc = person.to_jsonld()
    imported = import_from_jsonld(doc, PersonMap)
    assert imported.id == person.id
    assert imported.name == person.name
    assert imported.employer is not None
    assert imported.employer.id == 10
    assert imported.employer.name == "Analytical Engines Inc."


def test_turtle_round_trip() -> None:
    person = Person(
        id=2,
        name="Grace Hopper",
        employer=Organization(id=20, name="US Navy"),
    )
    turtle = person.to_rdf(format="turtle")
    imported = import_from_rdf(turtle, PersonMap, format="turtle")
    assert imported.id == 2
    assert imported.name == "Grace Hopper"
    assert imported.employer is not None
    assert imported.employer.id == 20


def test_from_jsonld_classmethod() -> None:
    person = Person(id=3, name="Test", employer=None)
    doc = person.to_jsonld()
    imported = Person.from_jsonld(doc, mapper=PersonMap)
    assert imported.id == 3
    assert imported.name == "Test"


def test_import_missing_id_raises() -> None:
    with pytest.raises(OntoImportError, match="Expected exactly one subject"):
        import_from_jsonld({"name": "No ID"}, PersonMap)


def test_import_wrong_type_raises() -> None:
    org = Organization(id=10, name="Acme")
    doc = org.to_jsonld()
    with pytest.raises(OntoImportError, match="rdf:type"):
        import_from_jsonld(doc, PersonMap)
