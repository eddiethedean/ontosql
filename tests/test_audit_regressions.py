"""Regression tests for the 22-bug security/QA audit fixes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Field, Session, SQLModel
from triplemodel import Store
from triplemodel.store.terms import term_str

from ontosql import Map, OntoMapper, OntoSession
from ontosql.compile.execute import ExecuteError
from ontosql.compile.write import compile_save_plan
from ontosql.export.jsonld import UnsafeJsonLdContextError, safe_document_loader
from ontosql.import_.hydrate import OntoImportError
from ontosql.import_.parse import load_graph
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, build_instance_iri
from ontosql.sync import StoreSyncTarget, push_instance, remove_instance
from ontosql.sync.graph import nested_iris_from_snapshot, sync_instance_to_store
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def test_upsert_null_clears_fk() -> None:
    class UpsertPersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.UPSERT,
        )

    person = Person(id=1, name="Ada", employer=None)
    plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"}, is_new=False)
    assert plan.nested == []
    assert plan.fk_updates.get("org_id") is None


def test_replace_cross_table_reference_blocks_delete(sync_engine) -> None:
    class BuildingRow(SQLModel, table=True):
        __tablename__ = "buildings"
        id: int | None = Field(default=None, primary_key=True)
        hq_org_id: int | None = Field(default=None, foreign_key="orgs.id")

    class Building(OntoModel):
        type_iri = "schema:Organization"
        id: int
        hq_org_id: int | None = None

    class BuildingMap(OntoMapper[Building]):
        entity = Building
        id = Map(BuildingRow.id)
        hq_org_id = Map(BuildingRow.hq_org_id)

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

    SQLModel.metadata.create_all(sync_engine, tables=[BuildingRow.__table__])  # type: ignore[attr-defined]
    with Session(sync_engine) as raw:
        raw.add(BuildingRow(id=1, hq_org_id=10))
        raw.commit()

    with OntoSession(sync_engine, maps=[ReplacePersonMap, OrganizationMap, BuildingMap]) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        person.employer = Organization(id=20, name="New Org")
        with pytest.raises(ExecuteError, match="still referenced"):
            session.save(person)


def test_stale_snapshot_merged_from_db_for_replace(sync_engine) -> None:
    class ReplacePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            property="schema:worksFor",
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.REPLACE,
        )

    with OntoSession(sync_engine, maps=[ReplacePersonMap, OrganizationMap]) as session:
        session.save(Organization(id=20, name="DB Org"))
        person = session.get(Person, identity=1)
        assert person is not None
        assert person.employer is not None
        assert person.employer.id == 10
        with Session(sync_engine) as raw:
            row = raw.get(PersonRow, 1)
            assert row is not None
            row.org_id = 20
            raw.commit()
        updated = Person(
            id=1,
            name="Ada",
            employer=Organization.model_construct(id=None, name="Fresh Org"),
        )
        session.save(updated)
    with Session(sync_engine) as raw:
        assert raw.get(OrgRow, 10) is not None
        assert raw.get(OrgRow, 20) is None


def test_graph_sync_retracts_stale_nested_org() -> None:
    reg = PrefixRegistry()
    org = Organization(id=10, name="Old Org")
    person = Person(id=1, name="Ada", employer=org)
    target = Store()
    push_instance(person, target, mode="replace", mapper=PersonMap)
    org_iri = build_instance_iri(org, reg)
    assert any(term_str(t[0]) == org_iri for t in target)

    cleared = Person(id=1, name="Ada", employer=None)
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    prior = nested_iris_from_snapshot(cleared, PersonMap, snapshot, reg)
    sync_instance_to_store(
        cleared,
        target,
        mode="patch",
        mapper_cls=PersonMap,
        prior_nested_iris=prior,
    )
    assert not any(term_str(t[0]) == org_iri for t in target)


def test_list_limit_negative_rejected(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person?limit=-1")
    assert resp.status_code == 422


def test_list_jsonld_mixed_accept(api_client: TestClient) -> None:
    resp = api_client.get(
        "/onto/person",
        headers={"Accept": "text/turtle;q=0.5, application/ld+json;q=0.9"},
    )
    assert resp.status_code == 200
    assert "application/ld+json" in resp.headers["content-type"]


def test_malformed_json_returns_400(api_client: TestClient) -> None:
    resp = api_client.post(
        "/onto/person",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_deep_json_rejected(api_client: TestClient) -> None:
    depth = 80
    payload = b"[" * depth + b"1" + b"]" * depth
    resp = api_client.post(
        "/onto/person",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_get_application_json(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person/1", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["name"] == "Ada Lovelace"


def test_list_limit_zero_rejected(api_client: TestClient) -> None:
    resp = api_client.get("/onto/person?limit=0")
    assert resp.status_code == 422


def test_session_graph_sync_uses_custom_registry(sync_engine) -> None:
    """Post-commit graph sync must honor session registry= (Bug #11)."""
    reg = PrefixRegistry.curated(extra={"ex": "https://example.org/ns/"})
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap],
        graph_sync=target,
        graph_sync_mode="replace",
        registry=reg,
    ) as session:
        session.save(Person(id=300, name="Registry Sync", employer=None))
    assert len(target.graph) > 0


def test_pending_delete_hidden_from_get(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        session.delete(person, flush_now=False)
        assert session.get(Person, identity=1) is None


def test_flush_partial_failure_preserves_retry(sync_engine) -> None:
    from unittest.mock import patch

    import ontosql.session.sync as sync_mod

    real_execute = sync_mod.execute_write_plan
    call_count = 0

    def flaky_execute(session, plan, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("fail")
        return real_execute(session, plan, **kwargs)

    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=90, name="A", employer=None), flush_now=False)
        session.save(Person(id=91, name="B", employer=None), flush_now=False)
        with patch.object(sync_mod, "execute_write_plan", side_effect=flaky_execute):
            with pytest.raises(RuntimeError, match="fail"):
                session.flush()
            session.flush()
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        assert session.get(Person, identity=90) is not None
        assert session.get(Person, identity=91) is not None


def test_get_iri_respects_identity_map(sync_engine) -> None:
    reg = PrefixRegistry()
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        a = session.get(Person, identity=1)
        assert a is not None
        a.name = "Edited In Session"
        iri = build_instance_iri(a, reg)
        b = session.get(Person, iri=iri)
        assert b is a


def test_double_deferred_save_single_insert(sync_engine) -> None:
    person = Person.model_construct(id=None, name="Once", employer=None)
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(person, flush_now=False)
        session.save(person, flush_now=False)
        assert len(session._state.pending) == 1  # noqa: SLF001
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        matches = session.find(Person, where=Person.name == "Once")
        assert len(matches) == 1


def test_deferred_insert_identity_merged(sync_engine) -> None:
    person = Person.model_construct(id=None, name="Deferred ID", employer=None)
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(person, flush_now=False)
        assert person.id is None
        session.flush()
        assert person.id is not None


def test_utf8_import_error() -> None:
    with pytest.raises(OntoImportError, match="UTF-8"):
        load_graph(b"\xff\xfe", format="turtle")


def test_safe_document_loader_blocks_remote() -> None:
    with pytest.raises(UnsafeJsonLdContextError):
        safe_document_loader("https://example.org/context.jsonld", {})


def test_delete_removes_exclusive_nested_graph() -> None:
    reg = PrefixRegistry()
    org = Organization(id=99, name="Solo Org")
    person = Person(id=5, name="Solo", employer=org)
    target = Store()
    push_instance(person, target, mode="replace", mapper=PersonMap)
    org_iri = build_instance_iri(org, reg)
    assert any(term_str(t[0]) == org_iri for t in target)

    solo = Person(id=5, name="Solo", employer=org)
    remove_instance(solo, target, mapper=PersonMap)
    assert not any(term_str(t[0]) == org_iri for t in target)


def test_zero_row_update_raises(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        ghost = Person(id=9999, name="Ghost", employer=None)
        session._state.register(ghost)  # noqa: SLF001
        with pytest.raises(ExecuteError, match="0 rows"):
            session.save(ghost)


def test_rollback_clears_pending_by_default(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=700, name="Rollback", employer=None), flush_now=False)
        session.rollback()
        assert not session._state.pending  # noqa: SLF001


@pytest.mark.asyncio
async def test_async_session_del_warns(async_engine) -> None:
    import gc

    from ontosql.session.async_session import AsyncOntoSession

    session = AsyncOntoSession(async_engine, maps=[PersonMap])
    await session.__aenter__()
    with pytest.warns(ResourceWarning, match="AsyncOntoSession"):
        del session
        gc.collect()


@pytest.fixture
def api_client(api_client_full: TestClient) -> TestClient:
    return api_client_full
