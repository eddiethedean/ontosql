"""Coverage for v0.3 write path, query, FastAPI, and optional JSON-LD."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel, create_engine

from ontosql.compile.execute import (
    async_execute_delete_plan,
    async_execute_write_plan,
    execute_delete_plan,
    execute_write_plan,
)
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.compile.select import _column_for_field, _order_column, compile_count_statement
from ontosql.compile.write import WriteCompileError, compile_delete_plan, compile_save_plan
from ontosql.export import jsonld as jsonld_module
from ontosql.fastapi.deps import get_async_onto_session, onto_session_lifespan
from ontosql.fastapi.openapi import enrich_openapi_schema, install_onto_openapi
from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.mapper import OntoMapper
from ontosql.query.expr import (
    Contains,
    EndsWith,
    FieldPath,
    FieldRef,
    OrderBy,
    compile_expr,
)
from ontosql.session.base import SessionBase
from ontosql.session.state import SessionState
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow

pytest.importorskip("fastapi")


def test_field_path_operators() -> None:
    col = PersonMap.column_maps["name"].column
    path = FieldPath(Person, ("employer", "name"))
    resolve = lambda ref: col  # noqa: E731
    compile_expr(path == "Acme", resolve)
    compile_expr(path.startswith("A"), resolve)
    compile_expr(path.contains("c"), resolve)
    compile_expr(path.endswith("e"), resolve)
    compile_expr(path.in_(["a"]), resolve)
    compile_expr(path.is_null(), resolve)
    assert isinstance(Person.employer.name, FieldPath)
    assert isinstance(Person.name.contains("x"), Contains)
    assert isinstance(Person.name.endswith("x"), EndsWith)
    assert OrderBy(Person.name, desc=True).desc is True


def test_column_for_field_errors() -> None:
    with pytest.raises(KeyError):
        _column_for_field(PersonMap, FieldPath(Person, ("missing",)))
    with pytest.raises(KeyError):
        _column_for_field(PersonMap, FieldRef(Person, "missing"))
    col = _column_for_field(PersonMap, FieldPath(Person, ("name",)))
    assert col is PersonRow.name
    assert _order_column(PersonMap, OrderBy(Person.name, desc=True)) is not None


def test_compile_count() -> None:
    stmt = compile_count_statement(PersonMap, where=Person.name.startswith("A"))
    assert "count" in str(stmt).lower()


def test_write_compile_errors() -> None:
    with pytest.raises(WriteCompileError, match="identity"):
        compile_delete_plan(PersonMap, Person.model_construct(id=None, name="x"))


def test_mapper_fk_column_required() -> None:
    from ontosql import Map

    class E(Person):
        pass

    with pytest.raises(ValueError, match="fk_column"):

        class BadMap(OntoMapper[E]):
            entity = E
            id = Map(PersonRow.id)
            employer = Map.nested(
                Organization,
                join=PersonRow.org_id == OrgRow.id,
                nested_map=OrganizationMap,
            )


def test_state_register_without_identity() -> None:
    state = SessionState()
    state.register(Person.model_construct(id=None, name="anon"))


def test_session_base_is_new_and_expire() -> None:
    base = SessionBase(maps=[PersonMap])
    person = Person(id=1, name="Ada", employer=None)
    assert base._is_new_instance(PersonMap, person) is True
    base._state.register(person)
    assert base._is_new_instance(PersonMap, person) is False
    with pytest.raises(TypeError):
        base.expire(dict, id=1)  # type: ignore[arg-type]


def test_execute_write_branches(sync_engine) -> None:
    with Session(sync_engine) as session:
        person = Person(id=70, name="Exec", employer=None)
        plan = compile_save_plan(PersonMap, person, is_new=True)
        assert execute_write_plan(session, plan) == 70

        person.name = "Exec2"
        update_plan = compile_save_plan(PersonMap, person, partial_fields={"name"})
        assert execute_write_plan(session, update_plan) == 70

        empty_update = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(table=PersonRow.__table__, values={}, where={"id": 70}),
            nested=[],
            fk_updates={},
        )
        assert execute_write_plan(session, empty_update) == 70

        delete_plan = compile_delete_plan(PersonMap, person)
        execute_delete_plan(session, delete_plan)


@pytest.mark.asyncio
async def test_async_execute_plans() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        person = Person(id=80, name="Async", employer=None)
        plan = compile_save_plan(PersonMap, person, is_new=True)
        assert await async_execute_write_plan(session, plan) == 80
        delete_plan = compile_delete_plan(PersonMap, person)
        await async_execute_delete_plan(session, delete_plan)
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_session_flush_and_deps(async_engine) -> None:
    from ontosql import AsyncOntoSession

    async with AsyncOntoSession(async_engine, maps=[PersonMap]) as session:
        person = Person(id=90, name="Pending", employer=None)
        await session.save(person, flush=False)
        await session.flush()
        loaded = await session.get(Person, id=90)
        assert loaded is not None

    app = FastAPI()
    onto_session_lifespan(app, async_engine, [PersonMap])

    async def _run() -> None:
        gen = get_async_onto_session(MagicMock(app=app))
        async for _s in gen:
            pass

    await _run()


def test_openapi_enrichment() -> None:
    app = FastAPI(title="Onto", version="0.3.0")
    schema = enrich_openapi_schema(app, [Person])
    assert "Person" in schema["components"]["schemas"]
    install_onto_openapi(app, [Person])
    assert app.openapi()["components"]["schemas"]["Person"]["x-ontosql-type-iri"]


def test_jsonld_import_error() -> None:
    with (
        patch.dict("sys.modules", {"pyld": None, "pyld.jsonld": None}),
        pytest.raises(ImportError, match="jsonld"),
    ):
        jsonld_module._require_pyld()


def test_jsonld_compact_frame() -> None:
    fake = MagicMock()
    fake.compact.return_value = {"@id": "x"}
    fake.frame.return_value = {"@graph": []}
    with patch.object(jsonld_module, "_require_pyld", return_value=fake):
        assert jsonld_module.compact_jsonld({}, {}) == {"@id": "x"}
        assert jsonld_module.frame_jsonld({}, {}) == {"@graph": []}


def test_router_skip_duplicate_register() -> None:
    from ontosql.fastapi.router import OntoRouter

    router = OntoRouter(maps=[PersonMap, OrganizationMap])
    router.register(Person)
    router.register(Person)
    assert len(router._entities) == 1


def test_router_list_jsonld() -> None:
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from ontosql.fastapi.deps import onto_session_lifespan
    from ontosql.fastapi.router import OntoRouter

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    app = FastAPI()
    onto_session_lifespan(app, engine, [PersonMap])
    router = OntoRouter(maps=[PersonMap])
    router.register(Person)
    router.include_in(app)
    client = TestClient(app)
    resp = client.get("/onto/person", headers={"Accept": "application/ld+json"})
    assert resp.status_code == 200
    assert "@graph" in resp.json()


def test_field_ref_private_attr_raises() -> None:
    ref = FieldRef(Person, "name")
    with pytest.raises(AttributeError):
        _ = ref._private  # noqa: SLF001


def test_field_path_private_attr_raises() -> None:
    path = FieldPath(Person, ("name",))
    with pytest.raises(AttributeError):
        _ = path._private  # noqa: SLF001


def test_execute_inserted_identity_branches() -> None:
    from ontosql.compile.execute import _inserted_identity, _update_identity

    plan = compile_save_plan(PersonMap, Person(id=1, name="A", employer=None), is_new=True)
    result = MagicMock(inserted_primary_key=(5,))
    assert _inserted_identity(result, plan, {"name": "A"}) == 5
    update_plan = compile_save_plan(
        PersonMap, Person(id=1, name="B", employer=None), partial_fields={"name"}
    )
    assert _update_identity(update_plan) == 1
    empty = WritePlan(
        mapper_cls=PersonMap,
        operation="update",
        root=TableWrite(table=PersonRow.__table__, values={}, where=None),
        nested=[],
        fk_updates={},
    )
    assert _update_identity(empty) is None


def test_write_cascade_branches() -> None:
    from ontosql import Map

    class IgnorePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.IGNORE,
        )

    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Acme"))
    plan = compile_save_plan(IgnorePersonMap, person)
    assert plan.nested == []
    assert plan.fk_updates == {}

    person2 = Person(id=1, name="Ada", employer=None)
    plan2 = compile_save_plan(PersonMap, person2, partial_fields={"employer"})
    assert plan2.fk_updates == {"org_id": None}

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

    org = Organization.model_construct(id=None, name="New")
    person3 = Person(id=1, name="Ada", employer=org)
    plan3 = compile_save_plan(UpsertPersonMap, person3, partial_fields={"employer"}, is_new=False)
    assert len(plan3.nested) == 1
    _, nested = plan3.nested[0]
    assert nested.operation == "insert"

    with pytest.raises(WriteCompileError, match="identity"):
        compile_save_plan(
            PersonMap,
            Person(
                id=1,
                name="Ada",
                employer=Organization.model_construct(id=None, name="X"),
            ),
            partial_fields={"employer"},
        )


def test_select_nested_field_not_on_mapper() -> None:
    with pytest.raises(KeyError, match="missing"):
        _column_for_field(PersonMap, FieldPath(Person, ("employer", "missing")))


def test_session_sync_pending_paths(sync_engine) -> None:
    from ontosql import OntoSession

    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        session.create_tables(PersonRow, OrgRow)
        person = Person(id=95, name="Queued", employer=None)
        assert session.save(person, flush=False).name == "Queued"
        pending_person = Person(id=96, name="Del", employer=None)
        session.save(pending_person)
        loaded = session.get(Person, id=96)
        assert loaded is not None
        session.delete(loaded, flush=False)
        session.flush()

        auto = Person.model_construct(name="Auto", id=None)
        saved = session.save(auto)
        assert saved.id is not None


def test_openapi_cached_schema() -> None:
    app = FastAPI(title="Onto", version="0.3.0")
    install_onto_openapi(app, [Person])
    first = app.openapi()
    second = app.openapi()
    assert first is second


@pytest.mark.asyncio
async def test_async_delete_pending_and_save(async_onto_session) -> None:
    person = await async_onto_session.get(Person, id=1)
    assert person is not None
    await async_onto_session.delete(person, flush=False)
    await async_onto_session.flush()

    new_person = Person(id=100, name="Async New", employer=None)
    await async_onto_session.save(new_person, flush=False)
    await async_onto_session.flush()
    assert await async_onto_session.get(Person, id=100) is not None


def test_state_identity_key() -> None:
    state = SessionState()
    person = Person(id=1, name="Ada", employer=None)
    assert state.identity_key(Person, person) == (Person, 1)


def test_router_patch_not_found() -> None:
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from ontosql.fastapi.deps import onto_session_lifespan
    from ontosql.fastapi.router import OntoRouter

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    app = FastAPI()
    onto_session_lifespan(app, engine, [PersonMap])
    router = OntoRouter(maps=[PersonMap])
    router.register(Person)
    router.include_in(app)
    client = TestClient(app)
    assert client.patch("/onto/person/999", json={"name": "X"}).status_code == 404


@pytest.mark.asyncio
async def test_async_execute_nested_and_empty_update() -> None:
    from ontosql import Map

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

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        org = Organization(id=30, name="Nested Async Org")
        person = Person(id=31, name="Nested", employer=org)
        plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"})
        await async_execute_write_plan(session, plan)
        empty = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(table=PersonRow.__table__, values={}, where={"id": 31}),
            nested=[],
            fk_updates={},
        )
        await async_execute_write_plan(session, empty)
        delete_no_where = DeletePlan(
            mapper_cls=PersonMap,
            root=TableWrite(table=PersonRow.__table__, where=None),
        )
        await async_execute_delete_plan(session, delete_no_where)
    await engine.dispose()


def test_remaining_coverage_gaps(sync_engine) -> None:
    from ontosql import Map, OntoSession
    from ontosql.compile.execute import _inserted_identity
    from ontosql.compile.write import _column_key, _fk_column_key
    from ontosql.mapping.map import NestedMap
    from ontosql.query.expr import Comparison
    from ontosql.session.base import SessionBase

    path = Person.employer.name
    compile_expr(Comparison(path, "ne", "x"), lambda ref: PersonRow.name)
    compile_expr(FieldPath(Person, ("name",)) != "z", lambda ref: PersonRow.name)

    with pytest.raises(KeyError, match="Nested field"):
        _column_for_field(PersonMap, FieldPath(Person, ("nope", "x")))

    assert _column_key(PersonRow.name) == "name"

    class BareCol:
        key = None
        name = None

    with pytest.raises(WriteCompileError):
        _column_key(BareCol())
    nmap = NestedMap(
        semantic_field="employer",
        entity_type=Organization,
        join=PersonRow.org_id == OrgRow.id,
        nested_mapper=OrganizationMap,
        fk_column=None,
    )
    with pytest.raises(WriteCompileError):
        _fk_column_key(nmap)

    with Session(sync_engine) as session:
        org = Organization(id=40, name="Nested Org")
        person = Person(id=41, name="Nested Person", employer=org)

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

        plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"})
        execute_write_plan(session, plan)

    plan_no_pk = MagicMock(mapper_cls=MagicMock(column_maps={}, identity_field="id"))
    result = MagicMock()
    result.inserted_primary_key = ()
    assert _inserted_identity(result, plan_no_pk, {}) is None

    class NameOnlyCol:
        key = None
        name = "only_name"

    assert _column_key(NameOnlyCol()) == "only_name"

    from ontosql.compile.write import _is_new_instance, _root_values

    fake_mapper = MagicMock()
    fake_mapper.__name__ = "Fake"
    fake_mapper.identity_field = "id"
    fake_mapper.column_maps = {"name": PersonMap.column_maps["name"]}
    with pytest.raises(WriteCompileError, match="identity column"):
        _is_new_instance(fake_mapper, Person(id=1, name="X", employer=None))

    dual_mapper = MagicMock()
    dual_mapper.column_maps = {"employer": PersonMap.column_maps["name"]}
    dual_mapper.nested_maps = {"employer": PersonMap.nested_maps["employer"]}
    dual_mapper.identity_field = "id"
    assert (
        _root_values(
            dual_mapper,
            Person(id=1, name="n", employer=None),
            partial_fields=None,
            include_identity=True,
        )
        == {}
    )

    bad_mapper = MagicMock()
    bad_mapper.__name__ = "Bad"
    bad_mapper.primary_table = None
    bad_mapper.column_maps = PersonMap.column_maps
    bad_mapper.nested_maps = {}
    bad_mapper.identity_field = "id"
    with pytest.raises(WriteCompileError):
        compile_save_plan(bad_mapper, Person(id=1, name="X", employer=None))
    bad_mapper.column_maps = {}
    with pytest.raises(WriteCompileError):
        compile_delete_plan(bad_mapper, Person.model_construct(id=None, name="X"))

    class ContextEntity:
        __name__ = "ContextPerson"
        type_iri = "schema:Person"
        jsonld_context = {"schema": "https://schema.org/"}

    app = FastAPI()
    schema = enrich_openapi_schema(app, [ContextEntity])  # type: ignore[list-item]
    assert "x-ontosql-context" in schema["components"]["schemas"]["ContextEntity"]

    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from ontosql.fastapi.router import OntoRouter

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    app2 = FastAPI()
    onto_session_lifespan(app2, engine, [PersonMap])
    router = OntoRouter(maps=[PersonMap])
    router.register(Person)
    router.include_in(app2)
    assert TestClient(app2).delete("/onto/person/404").status_code == 404

    base = SessionBase(maps=[PersonMap])
    person = Person(id=1, name="Ada", employer=None)
    base._state.register(person)
    base.expire(Person, id=1)
    base.rollback_pending()

    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        session.create_tables(PersonRow, OrgRow)
        session.delete(Person(id=999, name="Ghost", employer=None), flush=False)
        session.flush()
        session.save(Person(id=97, name="Keep", employer=None), flush=False)
        session.get(Person, iri="https://data.example.org/person/1")


def test_openapi_without_type_iri() -> None:
    from fastapi import FastAPI

    from ontosql.fastapi.openapi import enrich_openapi_schema

    class NoIri:
        __name__ = "NoIri"
        jsonld_context = {"ex": "http://example.org/"}

    app = FastAPI()
    schema = enrich_openapi_schema(app, [NoIri])  # type: ignore[list-item]
    assert "x-ontosql-context" in schema["components"]["schemas"]["NoIri"]
    assert "x-ontosql-type-iri" not in schema["components"]["schemas"]["NoIri"]


def test_count_scalar_async_tuple() -> None:
    from ontosql.session.async_session import _count_scalar

    assert _count_scalar((3,)) == 3


def test_count_scalar_tuple_branch() -> None:
    from ontosql.session.sync import _count_scalar

    assert _count_scalar((7,)) == 7
    assert _count_scalar(9) == 9


def test_openapi_existing_component() -> None:
    app = FastAPI()

    class Existing:
        __name__ = "Existing"
        type_iri = "schema:Person"
        jsonld_context = {"schema": "https://schema.org/"}

    with patch("ontosql.fastapi.openapi.get_openapi") as mock_openapi:
        mock_openapi.return_value = {
            "components": {"schemas": {"Existing": {"type": "object"}}},
        }
        schema = enrich_openapi_schema(app, [Existing])  # type: ignore[list-item]
        assert schema["components"]["schemas"]["Existing"]["x-ontosql-context"]


def test_field_path_attribute_error() -> None:
    path = FieldPath(Person, ("name",))
    with pytest.raises(AttributeError):
        _ = path._hidden  # noqa: SLF001


@pytest.mark.asyncio
async def test_async_session_remaining(async_onto_session) -> None:
    saved = await async_onto_session.save(Person(id=200, name="Queued", employer=None), flush=False)
    assert saved.name == "Queued"
    await async_onto_session.flush()
    assert await async_onto_session.get(Person, id=200) is not None
    await async_onto_session.get(
        Person,
        iri="https://data.example.org/person/1",
    )
