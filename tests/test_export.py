"""Tests for semantic instance export via TripleModel."""

from __future__ import annotations

from ontosql import OntoModel, PrefixRegistry, onto_property
from ontosql.export import instance_to_graph, instance_to_jsonld, instance_to_rdf
from tests.models import Organization, Person

EX_REGISTRY = PrefixRegistry(prefixes={"ex": "http://example.org/"})


class TaggedPerson(OntoModel):
    id: int
    tags: set[str] = onto_property("ex:tag")
    homepage: str = onto_property("ex:homepage")
    active: bool = onto_property("ex:active")
    note: str = onto_property("schema:name", iri="http://example.org/customNote")


def test_instance_to_rdf_nested() -> None:
    org = Organization(id=10, name="Analytical Engines Inc.")
    ada = Person(id=1, name="Ada Lovelace", employer=org)

    turtle = ada.to_rdf(format="turtle")
    assert "Ada Lovelace" in turtle
    assert "schema:Person" in turtle or "https://schema.org/Person" in turtle
    assert "schema:worksFor" in turtle or "https://schema.org/worksFor" in turtle


def test_instance_to_jsonld_has_context() -> None:
    ada = Person(id=1, name="Ada Lovelace", employer=None)
    doc = instance_to_jsonld(ada)
    assert "@context" in doc
    assert "schema" in doc["@context"]
    assert doc["@id"] == "https://data.example.org/person/1"


def test_instance_to_graph_round_trip() -> None:
    ada = Person(id=1, name="Ada Lovelace", employer=None)
    graph = instance_to_graph(ada)
    assert graph.serialize(format="nt")


def test_instance_to_rdf_via_module() -> None:
    ada = Person(id=1, name="Ada Lovelace", employer=None)
    body = instance_to_rdf(ada, format="turtle")
    assert "Ada Lovelace" in body


def test_export_custom_registry_and_field_variants() -> None:
    tagged = TaggedPerson(
        id=1,
        tags={"sql", "rdf"},
        homepage="https://example.org/ada",
        active=True,
        note="note",
    )
    turtle = tagged.to_rdf(registry=EX_REGISTRY)
    assert "https://example.org/ada" in turtle
    assert "note" in turtle
    doc = tagged.to_jsonld(registry=EX_REGISTRY)
    assert doc["@context"]["ex"] == "http://example.org/"


def test_export_skips_unmapped_fields() -> None:
    class Plain(OntoModel):
        type_iri = None
        id: int
        internal: str

    body = instance_to_rdf(Plain(id=1, internal="hidden"), format="nt")
    assert "hidden" not in body


def test_export_list_values() -> None:
    class Team(OntoModel):
        type_iri = "schema:Organization"
        id: int
        aliases: list[str] = onto_property("schema:alternateName")

    team = Team(id=1, aliases=["A", "B"])
    body = instance_to_rdf(team, format="turtle")
    assert "A" in body and "B" in body


def test_export_list_skips_none_items() -> None:
    class Team(OntoModel):
        type_iri = "schema:Organization"
        id: int
        aliases: list[str | None] = onto_property("schema:alternateName")

    team = Team(id=1, aliases=["A", None, "B"])
    body = instance_to_rdf(team, format="turtle")
    assert "A" in body and "B" in body


def test_export_revisit_same_instance() -> None:
    org = Organization(id=10, name="Acme")

    class CyclicPerson(OntoModel):
        type_iri = "schema:Person"
        iri_template = "https://data.example.org/person/{id}"

        id: int
        name: str = onto_property("schema:name")
        employer: Organization | None = onto_property("schema:worksFor")
        also_employer: Organization | None = onto_property("schema:memberOf")

    ada = CyclicPerson(id=1, name="Ada", employer=org, also_employer=org)
    graph = instance_to_graph(ada)
    assert graph.serialize(format="json-ld")


def test_export_list_of_nested_models() -> None:
    class Group(OntoModel):
        type_iri = "schema:Organization"
        id: int
        members: list[Organization] = onto_property("schema:member")

    org = Organization(id=10, name="Acme")
    group = Group(id=1, members=[org])
    body = instance_to_rdf(group, format="turtle")
    assert "Acme" in body


def test_instance_to_jsonld_dict_payload(monkeypatch) -> None:
    ada = Person(id=1, name="Ada Lovelace", employer=None)

    class FakeGraph:
        def serialize(self, *, format: str) -> str:
            return '{"@id": "https://data.example.org/person/1"}'

    monkeypatch.setattr(
        "ontosql.export.instance.instance_to_graph",
        lambda *a, **k: FakeGraph(),
    )
    doc = instance_to_jsonld(ada)
    assert doc["@id"] == "https://data.example.org/person/1"
    assert "@context" in doc


def test_instance_to_jsonld_graph_payload(monkeypatch) -> None:
    ada = Person(id=1, name="Ada Lovelace", employer=None)

    class FakeGraph:
        def serialize(self, *, format: str) -> str:
            return '[{"@id": "a"}, {"@id": "b"}]'

    monkeypatch.setattr(
        "ontosql.export.instance.instance_to_graph",
        lambda *a, **k: FakeGraph(),
    )
    doc = instance_to_jsonld(ada)
    assert "@graph" in doc
    assert len(doc["@graph"]) == 2
