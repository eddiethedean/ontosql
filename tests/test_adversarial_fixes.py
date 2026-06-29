"""Regression tests for adversarial audit fixes (v0.4.1)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pyoxigraph import Literal, NamedNode
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from triplemodel import Store
from triplemodel.store.terms import term_str

from ontosql import Map, OntoMapper, OntoSession
from ontosql.fastapi.deps import onto_session_lifespan
from ontosql.fastapi.router import OntoRouter
from ontosql.import_.hydrate import _coerce_literal
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import build_instance_iri
from ontosql.sync import StoreSyncTarget, push_instance
from ontosql.sync.graph import sync_instance_to_store as sync_to_store
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow

pytest.importorskip("fastapi")


def test_patch_cannot_retarget_id(api_client: TestClient) -> None:
    """PATCH must not update a different row when body includes id."""
    resp = api_client.patch("/onto/person/1", json={"name": "Hacked", "id": 999})
    assert resp.status_code == 400
    unchanged = api_client.get("/onto/person/1", headers={"Accept": "application/ld+json"})
    body = unchanged.json()
    names = [
        node.get("https://schema.org/name", [{}])[0].get("@value")
        for node in body.get("@graph", [])
        if "/person/" in node.get("@id", "")
    ]
    assert "Ada Lovelace" in names


def test_delete_flush_false_commits_on_exit(sync_engine) -> None:
    """Pending delete must flush on session exit."""
    target = StoreSyncTarget()
    with OntoSession(sync_engine, maps=[PersonMap], graph_sync=target) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        session.delete(person, flush_now=False)
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        assert session.get(Person, identity=1) is None


def test_delete_flush_false_graph_sync_on_exit(sync_engine) -> None:
    """Graph remove must run only after SQL delete on session exit."""
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        push_instance(person, target, mode="replace", mapper=PersonMap)
        assert len(target.graph) > 0
        session.delete(person, flush_now=False)
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        assert session.get(Person, identity=1) is None
    reg = PrefixRegistry()
    person_iri = build_instance_iri(Person(id=1, name="x", employer=None), reg)
    assert not any(term_str(t[0]) == person_iri for t in target.graph)


def test_save_flush_false_commits_on_exit(sync_engine) -> None:
    """Pending save must flush on session exit."""
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=200, name="Pending Save", employer=None), flush_now=False)
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        loaded = session.get(Person, identity=200)
        assert loaded is not None
        assert loaded.name == "Pending Save"


def test_clear_pending_clears_graph_sync(sync_engine) -> None:
    target = StoreSyncTarget()
    with OntoSession(sync_engine, maps=[PersonMap], graph_sync=target) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        push_instance(person, target, mode="replace", mapper=PersonMap)
        session.delete(person, flush_now=False)
        session.clear_pending()
    assert len(target.graph) > 0


def test_graph_patch_uses_root_iri_not_nested() -> None:
    """Patch mode must update root owned predicates and preserve foreign root triples."""
    person = Person(id=1, name="Ada", employer=None)
    target = Store()
    sync_to_store(person, target, mode="replace", mapper_cls=PersonMap)
    reg = PrefixRegistry()
    person_iri = build_instance_iri(person, reg)
    comment = NamedNode("http://www.w3.org/2000/01/rdf-schema#comment")
    target.add((NamedNode(person_iri), comment, Literal("external annotation")))

    person2 = Person(id=1, name="Ada Updated", employer=None)
    sync_to_store(person2, target, mode="patch", mapper_cls=PersonMap)
    comments = list(target.objects(NamedNode(person_iri), comment))
    assert len(comments) == 1
    name_pred = NamedNode(reg.expand("schema:name"))
    names = [str(getattr(o, "value", o)) for o in target.objects(NamedNode(person_iri), name_pred)]
    assert "Ada Updated" in names


def test_graph_sync_preserves_shared_nested_org() -> None:
    """Syncing one person must not fully wipe shared org subject triples."""
    reg = PrefixRegistry()
    org = Organization(id=10, name="Shared Org")
    person_a = Person(id=1, name="Ada", employer=org)
    person_b = Person(id=2, name="Bob", employer=org)
    target = Store()
    push_instance(person_a, target, mode="replace", mapper=PersonMap)
    push_instance(person_b, target, mode="replace", mapper=PersonMap)
    org_iri = build_instance_iri(org, reg)
    ext_pred = NamedNode("http://example.org/external")
    target.add((NamedNode(org_iri), ext_pred, Literal("third-party fact")))

    person_a_updated = Person(id=1, name="Ada L.", employer=org)
    push_instance(person_a_updated, target, mode="patch", mapper=PersonMap)
    ext_values = list(target.objects(NamedNode(org_iri), ext_pred))
    assert len(ext_values) == 1


def test_replace_loads_snapshot_from_db() -> None:
    """REPLACE cascade must use DB state when session snapshot is missing."""
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as raw:
        raw.add(OrgRow(id=10, name="Old Org"))
        raw.add(PersonRow(id=1, name="Ada", org_id=10))
        raw.commit()

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

    with OntoSession(engine, maps=[ReplacePersonMap, OrganizationMap]) as session:
        updated = Person(
            id=1,
            name="Ada",
            employer=Organization.model_construct(name="New Lab", id=None),
        )
        session.save(updated)
    with OntoSession(engine, maps=[ReplacePersonMap, OrganizationMap]) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        assert person.employer is not None
        with Session(engine) as raw:
            assert raw.get(OrgRow, 10) is None
            assert raw.get(OrgRow, person.employer.id) is not None


def test_coerce_optional_int() -> None:
    reg = PrefixRegistry()
    value = _coerce_literal(Literal("42"), py_type=int | None, registry=reg, meta={})
    assert value == 42
    assert isinstance(value, int)


def test_list_persons_turtle(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person", headers={"Accept": "text/turtle"})
    assert resp.status_code == 200
    assert "text/turtle" in resp.headers["content-type"]
    assert "Ada Lovelace" in resp.text


def test_invalid_graph_sync_mode_raises() -> None:
    from ontosql.sync.graph import sync_instance_to_store

    person = Person(id=1, name="Ada", employer=None)
    target = Store()
    with pytest.raises(ValueError, match="Unknown graph sync mode"):
        sync_instance_to_store(person, target, mode="pach", mapper_cls=PersonMap)  # type: ignore[arg-type]


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
    router.include_in(app)
    return TestClient(app)
