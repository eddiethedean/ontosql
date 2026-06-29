"""Regression tests for second-pass subtle bug audit fixes."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from triplemodel.store.terms import term_str

from ontosql import Map, OntoMapper, OntoSession
from ontosql.compile.execute import ExecuteError
from ontosql.compile.write import WriteCompileError, compile_save_plan
from ontosql.export.jsonld import compact_jsonld
from ontosql.fastapi.negotiate import _parse_accept, parse_accept_mime
from ontosql.mapping.cascade import CascadePolicy
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import build_instance_iri
from ontosql.sync import StoreSyncTarget
from tests.conftest import graph_object_iris
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow
from tests.models_m2m import (
    M2MPersonRow,
    PersonSkillRow,
    Skill,
    SkilledPerson,
    SkilledPersonMap,
    SkillMap,
    SkillRow,
)


def test_session_graph_sync_retracts_stale_nested_on_clear_employer(sync_engine) -> None:
    """Session path must capture pre-save nested IRIs (H1)."""
    reg = PrefixRegistry()
    target = StoreSyncTarget()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="patch",
    ) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        assert person.employer is not None
        session.save(person)

    org_iri = build_instance_iri(Organization(id=10, name="Analytical Engines Inc."), reg)
    assert any(term_str(t[0]) == org_iri for t in target.graph)

    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="patch",
    ) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        person.employer = None
        session.save(person)

    assert not any(term_str(t[0]) == org_iri for t in target.graph)


def test_find_excludes_pending_delete(sync_engine) -> None:
    """find() must respect pending-delete tombstones (H3)."""
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        session.delete(person, flush_now=False)
        ids = {p.id for p in session.find(Person)}
        assert 1 not in ids


def test_exception_exit_clears_pending_queue(sync_engine) -> None:
    """Reused session must not flush stale pending after exception (H5)."""
    session = OntoSession(sync_engine, maps=[PersonMap])
    with pytest.raises(RuntimeError, match="boom"), session:
        session.save(Person(id=800, name="Stale", employer=None), flush_now=False)
        raise RuntimeError("boom")
    with session:
        assert not session._state.pending  # noqa: SLF001
    with OntoSession(sync_engine, maps=[PersonMap]) as check:
        assert check.get(Person, identity=800) is None


def test_flush_failure_preserves_deferred_insert_identity(sync_engine) -> None:
    """Mid-flush failure must not drop pending_instances mapping (H4)."""
    import ontosql.session.sync as sync_mod

    real_execute = sync_mod.execute_write_plan
    call_count = 0
    person = Person.model_construct(id=None, name="FlushRecover", employer=None)

    def flaky_execute(session, plan, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("fail once")
        return real_execute(session, plan, **kwargs)

    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(person, flush_now=False)
        with patch.object(sync_mod, "execute_write_plan", side_effect=flaky_execute):
            with pytest.raises(RuntimeError, match="fail once"):
                session.flush()
            session.flush()
        assert person.id is not None


def test_db_null_snapshot_clears_stale_nested_for_replace(sync_engine) -> None:
    """DB-null FK must override session nested snapshot (M1)."""

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

    with Session(sync_engine) as raw:
        row = raw.get(PersonRow, 1)
        assert row is not None
        row.org_id = None
        raw.commit()

    with OntoSession(sync_engine, maps=[ReplacePersonMap, OrganizationMap]) as session:
        session._state.register(  # noqa: SLF001
            Person(
                id=1,
                name="Ada Lovelace",
                employer=Organization(id=10, name="Analytical Engines Inc."),
            )
        )
        person = Person(id=1, name="Ada Lovelace", employer=None)
        session.save(person)

    with Session(sync_engine) as raw:
        assert raw.get(OrgRow, 10) is not None


def test_replace_compile_requires_snapshot_on_update() -> None:
    """Direct compile callers must pass snapshot for REPLACE updates (M10)."""

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

    person = Person(id=1, name="Ada", employer=Organization(id=20, name="New"))
    with pytest.raises(WriteCompileError, match="requires snapshot"):
        compile_save_plan(ReplacePersonMap, person, is_new=False, snapshot=None)


def test_accept_json_loses_to_higher_q_ldjson() -> None:
    """application/json must not beat higher-q application/ld+json (M2)."""
    header = "application/json;q=0.1, application/ld+json;q=0.9"
    assert parse_accept_mime(header) == "application/ld+json"
    assert _parse_accept(header) == "application/ld+json"


def test_list_json_beats_ldjson_when_higher_q(api_client: TestClient) -> None:
    resp = api_client.get(
        "/onto/person",
        headers={"Accept": "application/json;q=0.9, application/ld+json;q=0.1"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert isinstance(resp.json(), list)


def test_allow_remote_contexts_requires_loader() -> None:
    with pytest.raises(ValueError, match="document_loader"):
        compact_jsonld({}, {}, allow_remote_contexts=True)


def test_execute_replace_requires_mapper_registry(sync_engine) -> None:
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

    from ontosql.compile.execute import execute_write_plan

    person = Person(id=1, name="Ada", employer=Organization(id=99, name="New"))
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old"}}
    plan = compile_save_plan(
        ReplacePersonMap,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    with Session(sync_engine) as session, pytest.raises(ExecuteError, match="mapper_registry"):
        execute_write_plan(session, plan)


@pytest.fixture
def m2m_graph_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(M2MPersonRow(id=1, name="Ada"))
        session.add(SkillRow(id=10, name="SQL"))
        session.add(SkillRow(id=11, name="RDF"))
        session.add(SkillRow(id=12, name="SPARQL"))
        session.add(PersonSkillRow(person_id=1, skill_id=10))
        session.add(PersonSkillRow(person_id=1, skill_id=11))
        session.commit()
    yield engine
    engine.dispose()


def test_graph_sync_collection_patch_retracts_stale_skills(m2m_graph_engine) -> None:
    """Collection predicates must be owned in patch mode (H2)."""
    reg = PrefixRegistry()
    target = StoreSyncTarget()
    with OntoSession(
        m2m_graph_engine,
        maps=[SkilledPersonMap, SkillMap],
        graph_sync=target,
        graph_sync_mode="patch",
    ) as session:
        person = session.get(SkilledPerson, identity=1)
        assert person is not None
        session.save(person)

    skill10 = build_instance_iri(Skill(id=10, name="SQL"), reg)
    skill11 = build_instance_iri(Skill(id=11, name="RDF"), reg)
    assert any(term_str(t[0]) == skill10 for t in target.graph)
    assert any(term_str(t[0]) == skill11 for t in target.graph)

    with OntoSession(
        m2m_graph_engine,
        maps=[SkilledPersonMap, SkillMap],
        graph_sync=target,
        graph_sync_mode="patch",
    ) as session:
        person = session.get(SkilledPerson, identity=1)
        assert person is not None
        person.skills = [Skill(id=12, name="SPARQL")]
        session.save(person)

    person_iri = build_instance_iri(SkilledPerson(id=1, name="Ada"), reg)
    linked = set(graph_object_iris(target.graph, person_iri, "schema:knowsAbout", registry=reg))
    assert skill10 not in linked
    assert skill11 not in linked
    assert build_instance_iri(Skill(id=12, name="SPARQL"), reg) in linked


def test_rollback_clear_uow_false_warns(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=801, name="Warn", employer=None), flush_now=False)
        with pytest.warns(UserWarning, match="clear_uow=False"):
            session.rollback(clear_uow=False)


@pytest.fixture
def api_client(api_client_full: TestClient) -> TestClient:
    return api_client_full
