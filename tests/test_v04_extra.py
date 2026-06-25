"""Additional import and session graph_sync coverage."""

from __future__ import annotations

import pytest

from ontosql import Map, OntoMapper, OntoSession
from ontosql.import_ import OntoImportError, graph_to_instance, import_from_rdf, load_graph
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, onto_property
from ontosql.shacl import shapes_from_mappers, validate_instance
from ontosql.sync import StoreSyncTarget
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def test_import_from_rdf_auto_subject() -> None:
    person = Person(id=5, name="Auto", employer=None)
    turtle = person.to_rdf(format="turtle")
    imported = import_from_rdf(turtle, PersonMap, format="turtle")
    assert imported.id == 5


def test_import_from_rdf_multiple_subjects_raises() -> None:
    turtle = (
        "@prefix schema: <https://schema.org/> .\n"
        "<https://data.example.org/person/1> a schema:Person .\n"
        "<https://data.example.org/person/2> a schema:Person .\n"
    )
    with pytest.raises(OntoImportError, match="Expected exactly one subject"):
        import_from_rdf(turtle, PersonMap, format="turtle")


def test_graph_to_instance_requires_iri() -> None:
    graph = load_graph("@prefix schema: <https://schema.org/> .\n", format="turtle")
    with pytest.raises(OntoImportError, match="requires iri"):
        graph_to_instance(graph, PersonMap)


def test_session_graph_sync_on_save(sync_engine) -> None:
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        person = Person(id=80, name="Synced", employer=None)
        session.save(person)
    assert len(target.graph) > 0


def test_replace_cascade_integration(sync_engine) -> None:
    class ReplacePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.REPLACE,
        )

    with OntoSession(sync_engine, maps=[ReplacePersonMap, OrganizationMap]) as session:
        session.save(Organization(id=20, name="Other Org"))
        person = session.get(Person, id=1)
        assert person is not None
        person.employer = Organization(id=20, name="Other Org")
        session.save(person)
        reloaded = session.get(Person, id=1)
        assert reloaded is not None
        assert reloaded.employer is not None
        assert reloaded.employer.id == 20


def test_shapes_from_mappers_and_validate() -> None:
    pytest.importorskip("pyshacl")
    shapes = shapes_from_mappers([PersonMap, OrganizationMap])
    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Acme"))
    report = validate_instance(person, PersonMap, shapes=shapes)
    assert report.conforms is True


def test_onto_model_from_jsonld_type_error() -> None:
    org = Organization(id=10, name="Acme")
    doc = org.to_jsonld()
    with pytest.raises(TypeError, match="Expected Person"):
        Person.from_jsonld(doc, mapper=OrganizationMap)


class TypedLabel(OntoModel):
    type_iri = "schema:Thing"
    iri_template = "https://data.example.org/thing/{id}"

    id: int
    label: str = onto_property("schema:name", language="en")


def test_export_import_language_tag() -> None:
    class ThingMap(OntoMapper[TypedLabel]):
        entity = TypedLabel
        id = Map(PersonRow.id)
        label = Map(PersonRow.name, property="schema:name")

    thing = TypedLabel(id=1, label="Hello")
    doc = thing.to_jsonld()
    from ontosql.import_ import import_from_jsonld

    imported = import_from_jsonld(doc, ThingMap)
    assert imported.label == "Hello"


def test_sync_add_mode() -> None:
    from triplemodel import Store

    from ontosql.sync.graph import sync_instance_to_store

    person = Person(id=90, name="Add Mode", employer=None)
    target = Store()
    sync_instance_to_store(person, target, mode="add", mapper_cls=PersonMap)
    sync_instance_to_store(person, target, mode="add", mapper_cls=PersonMap)
    assert len(target) >= 2


def test_import_coerce_bool() -> None:
    from pyoxigraph import Literal

    from ontosql.import_.hydrate import _coerce_literal

    assert (
        _coerce_literal(Literal("true"), py_type=bool, registry=PrefixRegistry(), meta={}) is True
    )


def test_prefix_registry_curated_vocab() -> None:
    reg = PrefixRegistry.curated("schema_org", vocab="https://schema.org/")
    assert reg.expand("Person") == "https://schema.org/Person"
