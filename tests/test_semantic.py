"""Tests for OntoModel and onto_property."""

from __future__ import annotations

from ontosql import OntoModel, onto_property
from ontosql.semantic.model import build_instance_iri, get_onto_property_meta, parse_iri_id
from tests.models import Organization, Person


def test_onto_property_metadata() -> None:
    meta = get_onto_property_meta(Person, "name")
    assert meta["ontology"] == "schema:name"


def test_build_instance_iri() -> None:
    person = Person(id=1, name="Ada", employer=None)
    assert build_instance_iri(person) == "https://data.example.org/person/1"


def test_parse_iri_id() -> None:
    assert parse_iri_id("https://data.example.org/person/42", Person) == 42
    assert parse_iri_id("https://wrong.example.org/person/42", Person) is None


def test_parse_iri_no_template() -> None:
    class NoTpl(OntoModel):
        id: int

    assert parse_iri_id("http://x", NoTpl) is None


def test_type_iri_on_model() -> None:
    assert Person.type_iri == "schema:Person"
    assert Organization.type_iri == "schema:Organization"


def test_onto_model_is_pydantic() -> None:
    p = Person(id=1, name="Test", employer=None)
    assert isinstance(p, OntoModel)
    assert p.model_dump()["name"] == "Test"


class MinimalEntity(OntoModel):
    type_iri = "schema:Thing"
    id: int
    label: str = onto_property("schema:name")


def test_query_field_ref_on_class() -> None:
    ref = Person.name
    assert ref.field_name == "name"
    assert ref.model is Person
