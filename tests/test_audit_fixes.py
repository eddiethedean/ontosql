"""Tests for adversarial audit bug fixes."""

from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode
from triplemodel import Store

from ontosql import Map, OntoMapper, OntoSession
from ontosql.compile.execute import ExecuteError
from ontosql.import_.hydrate import OntoImportError, _coerce_literal, graph_to_instance
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from ontosql.sync import StoreSyncTarget, push_instance
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def _replace_person_map() -> type[OntoMapper[Person]]:
    class ReplacePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name, property="schema:name")
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            property="schema:worksFor",
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.REPLACE,
        )

    return ReplacePersonMap


def test_push_instance_patch_preserves_foreign_triples() -> None:
    """StoreSyncTarget patch must not wipe non-owned triples (Bug 2)."""
    person = Person(id=1, name="Ada", employer=None)
    target = StoreSyncTarget()
    push_instance(person, target, mode="replace", mapper_cls=PersonMap)
    reg = PrefixRegistry()
    subject = NamedNode("https://data.example.org/person/1")
    comment = NamedNode("http://www.w3.org/2000/01/rdf-schema#comment")
    target.graph.add((subject, comment, Literal("external annotation")))
    person2 = Person(id=1, name="Updated", employer=None)
    push_instance(person2, target, mode="patch", mapper_cls=PersonMap)
    comments = list(target.graph.objects(subject, comment))
    assert len(comments) == 1
    names = [
        str(getattr(o, "value", o))
        for o in target.graph.objects(subject, NamedNode(reg.expand("schema:name")))
    ]
    assert "Updated" in names


def test_graph_sync_deferred_until_commit(sync_engine) -> None:
    """Graph must not update until SQL transaction commits (Bug 1)."""
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        session.save(Person(id=90, name="Deferred", employer=None))
        assert len(target.graph) == 0
    assert len(target.graph) > 0


def test_graph_sync_rollback_discards_queue(sync_engine) -> None:
    target = StoreSyncTarget()
    with (
        pytest.raises(RuntimeError, match="abort"),
        OntoSession(
            sync_engine,
            maps=[PersonMap],
            graph_sync=target,
            graph_sync_mode="replace",
        ) as session,
    ):
        session.save(Person(id=91, name="No Graph", employer=None))
        raise RuntimeError("abort")
    assert len(target.graph) == 0


def test_graph_sync_on_delete(sync_engine) -> None:
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        person = session.get(Person, id=1)
        assert person is not None
        session.delete(person)
    assert not any(str(t[0]).endswith("/person/1") for t in target.graph)


def test_replace_shared_nested_raises(sync_engine) -> None:
    """REPLACE must not delete nested rows still referenced elsewhere (Bug 3)."""
    mapper = _replace_person_map()
    with OntoSession(sync_engine, maps=[mapper, OrganizationMap]) as session:
        session.save(Organization(id=20, name="Other Org"))
        person = session.get(Person, id=1)
        assert person is not None
        person.employer = Organization(id=20, name="Other Org")
        with pytest.raises(ExecuteError, match="still referenced"):
            session.save(person)


def test_replace_inserts_new_nested_for_solo_person(sync_engine) -> None:
    mapper = _replace_person_map()
    with OntoSession(sync_engine, maps=[mapper, OrganizationMap]) as session:
        person = session.get(Person, id=3)
        assert person is not None
        assert person.employer is None
        person.employer = Organization.model_construct(id=None, name="Solo Org")
        session.save(person)
        reloaded = session.get(Person, id=3)
        assert reloaded is not None
        assert reloaded.employer is not None
        assert reloaded.employer.name == "Solo Org"


def test_snapshot_survives_model_copy_on_save(sync_engine) -> None:
    """Snapshot keyed by identity supports detached copies (Bug 5)."""
    mapper = _replace_person_map()
    with OntoSession(sync_engine, maps=[mapper, OrganizationMap]) as session:
        session.save(Organization(id=30, name="Target Org"))
        original = session.get(Person, id=3)
        assert original is not None
        updated = original.model_copy(update={"employer": Organization(id=30, name="Target Org")})
        session.save(updated)
        reloaded = session.get(Person, id=3)
        assert reloaded is not None
        assert reloaded.employer is not None
        assert reloaded.employer.id == 30


def test_coerce_literal_invalid_int_raises() -> None:
    reg = PrefixRegistry()
    with pytest.raises(OntoImportError, match="int"):
        _coerce_literal(Literal("not-a-number"), py_type=int, registry=reg, meta={})


def test_coerce_literal_invalid_bool_raises() -> None:
    reg = PrefixRegistry()
    with pytest.raises(OntoImportError, match="bool"):
        _coerce_literal(Literal("maybe"), py_type=bool, registry=reg, meta={})


def test_graph_to_instance_cycle_raises() -> None:
    graph = Store()
    reg = PrefixRegistry()
    person_iri = "https://data.example.org/person/1"
    graph.parse(
        f"""
        @prefix schema: <https://schema.org/> .
        <{person_iri}> a schema:Person ;
            schema:name "Ada" .
        """,
        format="turtle",
    )
    with pytest.raises(OntoImportError, match="Circular"):
        graph_to_instance(
            graph,
            PersonMap,
            iri=person_iri,
            registry=reg,
            _visited={person_iri},
        )


def test_flush_queues_graph_sync(sync_engine) -> None:
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        session.save(Person(id=92, name="Flush Sync", employer=None), flush=False)
        assert len(target.graph) == 0
        session.flush()
        assert len(target.graph) == 0
    assert len(target.graph) > 0
