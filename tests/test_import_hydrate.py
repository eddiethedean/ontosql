"""Unit tests for import hydrate helpers."""

from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode
from triplemodel import RDF_TYPE, Store

from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property
from ontosql.export.instance import instance_to_graph
from ontosql.import_.hydrate import (
    OntoImportError,
    _coerce_identity,
    _coerce_literal,
    _resolve_registry,
    _validate_type,
    graph_to_instance,
    subject_iri_from_jsonld,
)
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from tests.models import OrgRow, Person, PersonMap
from tests.models_m2m import (
    M2MPersonRow,
    PersonSkillRow,
    Skill,
    SkilledPerson,
    SkillMap,
    SkillRow,
)


def test_resolve_registry_explicit() -> None:
    custom = PrefixRegistry({"ex": "https://example.org/"})
    reg = _resolve_registry(PersonMap, custom)
    assert reg is custom


def test_resolve_registry_default() -> None:
    reg = _resolve_registry(PersonMap, None)
    assert reg.expand("schema:name") == "https://schema.org/name"


def test_coerce_identity_from_iri() -> None:
    value = _coerce_identity(
        NamedNode("https://data.example.org/person/7"),
        Person,
        registry=PrefixRegistry(),
    )
    assert value == 7


def test_coerce_literal_int_float() -> None:
    reg = PrefixRegistry()
    assert _coerce_literal(Literal("42"), py_type=int, registry=reg, meta={}) == 42
    assert _coerce_literal(Literal("3.5"), py_type=float, registry=reg, meta={}) == 3.5
    assert _coerce_literal(Literal("false"), py_type=bool, registry=reg, meta={}) is False


def test_validate_type_missing_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    with pytest.raises(OntoImportError, match="rdf:type"):
        _validate_type(graph, subject, Person, PrefixRegistry())


def test_subject_iri_from_jsonld() -> None:
    assert subject_iri_from_jsonld({"@id": "https://example.org/x"}) == "https://example.org/x"


def test_subject_iri_from_jsonld_missing() -> None:
    with pytest.raises(OntoImportError):
        subject_iri_from_jsonld({})


class Team(OntoModel):
    type_iri = "schema:Organization"
    iri_template = "https://data.example.org/team/{id}"

    id: int
    aliases: list[str] = onto_property("schema:alternateName")


class TeamMap(OntoMapper[Team]):
    entity = Team
    primary_table = OrgRow.__table__  # type: ignore[attr-defined]
    id = Map(OrgRow.id)
    aliases = Map(OrgRow.name, property="schema:alternateName")


def test_import_multi_valued_list_round_trip() -> None:
    team = Team(id=1, aliases=["Alpha", "Beta"])
    graph = instance_to_graph(team)
    iri = "https://data.example.org/team/1"
    restored = graph_to_instance(graph, TeamMap, iri=iri)
    assert sorted(restored.aliases) == ["Alpha", "Beta"]


def test_import_nested_literal_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    graph.add(
        (
            subject,
            NamedNode("https://schema.org/worksFor"),
            Literal("not-a-uri"),
        )
    )
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("Ada")))
    with pytest.raises(OntoImportError, match="URI object"):
        graph_to_instance(
            graph,
            PersonMap,
            iri="https://data.example.org/person/1",
        )


def test_graph_to_instance_validation_error_wrapped() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    with pytest.raises(OntoImportError, match="Cannot validate"):
        graph_to_instance(
            graph,
            PersonMap,
            iri="https://data.example.org/person/1",
        )


def test_import_collection_m2m_round_trip() -> None:
    from sqlmodel import Session, SQLModel, create_engine

    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(M2MPersonRow(id=1, name="Ada"))
        session.add(SkillRow(id=10, name="SQL"))
        session.add(PersonSkillRow(person_id=1, skill_id=10))
        session.commit()

    class ReplaceSkillsPersonMap(OntoMapper[SkilledPerson]):
        entity = SkilledPerson
        id = Map(M2MPersonRow.id)
        name = Map(M2MPersonRow.name, property="schema:name")
        skills = Map.collection(
            Skill,
            through=PersonSkillRow,
            source_fk=PersonSkillRow.person_id,
            target_fk=PersonSkillRow.skill_id,
            nested_map=SkillMap,
            field="skills",
            property="schema:knowsAbout",
            cascade=CascadePolicy.LINK,
        )

    with OntoSession(engine, maps=[ReplaceSkillsPersonMap, SkillMap]) as session:
        person = session.get(SkilledPerson, identity=1)
        assert person is not None
        graph = instance_to_graph(person)
        restored = graph_to_instance(
            graph,
            ReplaceSkillsPersonMap,
            iri="https://data.example.org/person/1",
        )
        assert len(restored.skills) == 1
        assert restored.skills[0].name == "SQL"
