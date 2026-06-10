"""Targeted edge-case tests for modules not covered by integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from ontosql import OntoSession
from ontosql.compile.execute import async_execute_write_plan, execute_write_plan
from ontosql.compile.plan import TableWrite, WritePlan
from ontosql.compile.write import WriteCompileError, compile_save_plan
from ontosql.fastapi.deps import get_async_onto_session, onto_session_lifespan
from ontosql.fastapi.negotiate import _parse_accept, negotiate_onto_response
from ontosql.fastapi.responses import NTriplesResponse, RDFXMLResponse, TurtleResponse
from ontosql.mapping.map import Map as MapCls
from ontosql.mapping.registry import MapperRegistry
from ontosql.query.expr import FieldRef, compile_expr
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, build_instance_iri, get_onto_property_meta
from ontosql.session.base import SessionBase
from ontosql.session.state import SessionState
from tests.models import Person, PersonMap, PersonRow

pytest.importorskip("fastapi")


def test_parse_accept_text_wildcard() -> None:
    assert _parse_accept("text/*") == "text/turtle"


def test_negotiate_unknown_accept_falls_back_to_jsonld(monkeypatch: pytest.MonkeyPatch) -> None:
    request = MagicMock()
    request.headers.get.return_value = "text/turtle"
    from ontosql.fastapi import negotiate as neg

    monkeypatch.setattr(neg, "_parse_accept", lambda _a: "unknown/mime")
    resp = negotiate_onto_response(request, {"@id": "http://ex/x"})
    assert resp.media_type == "application/ld+json"


def test_response_classes_render() -> None:
    assert TurtleResponse("@prefix x: <http://ex/> .").media_type == "text/turtle"
    assert NTriplesResponse("<s> <p> <o> .").media_type == "application/n-triples"
    assert RDFXMLResponse("<rdf/>").media_type == "application/rdf+xml"


def test_registry_compact_and_context_edges() -> None:
    reg = PrefixRegistry()
    assert reg.compact("not-an-iri") == "not-an-iri"
    ctx = PrefixRegistry().with_vocab("http://example.org/").context_dict()
    assert ctx["@vocab"] == "http://example.org/"


def test_mapper_registry_get_missing() -> None:
    reg = MapperRegistry()
    with pytest.raises(KeyError):
        reg.get(Person)


def test_field_ref_comparison_operators() -> None:
    col = PersonMap.column_maps["name"].column
    resolve = lambda ref: col  # noqa: E731
    ref = FieldRef(Person, "name")
    for expr in (ref != "x", ref < "x", ref <= "x", ref > "x", ref >= "x", ref.in_(["a"])):
        compile_expr(expr, resolve)


def test_build_iri_missing_template_field() -> None:
    class Bad(OntoModel):
        type_iri = "schema:Thing"
        iri_template = "http://ex/{missing}"
        id: int
        name: str

    assert build_instance_iri(Bad(id=1, name="n")) == "http://example.org/bad/1"


def test_session_base_expire_and_is_new() -> None:
    base = SessionBase(maps=[PersonMap])
    person = Person(id=1, name="Ada", employer=None)
    assert base._is_new_instance(PersonMap, person) is True
    base._state.register(person)
    assert base._is_new_instance(PersonMap, person) is False
    base.expire(Person, id=1)
    with pytest.raises(TypeError):
        base.expire(dict, id=1)  # type: ignore[arg-type]


def test_state_register_without_identity() -> None:
    state = SessionState()
    state.register(Person.model_construct(id=None, name="anon"))


@pytest.mark.asyncio
async def test_async_session_deps(async_engine) -> None:
    app = FastAPI()
    onto_session_lifespan(app, async_engine, [PersonMap])

    async def _run() -> None:
        gen = get_async_onto_session(MagicMock(app=app))
        async for session in gen:
            assert session is not None

    await _run()


@pytest.mark.asyncio
async def test_async_execute_update_path() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        person = Person(id=81, name="AsyncUp", employer=None)
        insert_plan = compile_save_plan(PersonMap, person, is_new=True)
        await async_execute_write_plan(session, insert_plan)
        person.name = "AsyncUp2"
        update_plan = compile_save_plan(PersonMap, person, partial_fields={"name"})
        assert await async_execute_write_plan(session, update_plan) == 81
    await engine.dispose()


def test_execute_update_without_where_updates_all_matching(sync_engine) -> None:
    from sqlmodel import Session

    with Session(sync_engine) as session:
        plan = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(
                table=PersonRow.__table__,
                values={"name": "BulkRename"},
                where=None,
            ),
            nested=[],
            fk_updates={},
        )
        execute_write_plan(session, plan)


def test_map_column_infer_and_nested_errors() -> None:
    m = MapCls(PersonMap.column_maps["name"].column, field="custom")
    assert m.semantic_field == "custom"

    from ontosql.mapping.map import NestedMap

    nm = NestedMap("x", Person, PersonMap.column_maps["id"].column == 1, object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="no primary_table"):
        _ = nm.target_table


def test_compile_save_missing_primary_table() -> None:
    bad = MagicMock()
    bad.__name__ = "Bad"
    bad.primary_table = None
    bad.column_maps = PersonMap.column_maps
    bad.nested_maps = {}
    bad.identity_field = "id"
    with pytest.raises(WriteCompileError):
        compile_save_plan(bad, Person(id=1, name="X", employer=None))


def test_onto_property_callable_extra() -> None:
    from pydantic import Field

    def extra() -> dict:
        return {}

    class M(OntoModel):
        id: int
        x: str = Field(default="a", json_schema_extra=extra)

    assert get_onto_property_meta(M, "x") == {}


def test_sync_create_tables(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.create_tables(PersonRow)


def test_inserted_identity_from_values() -> None:
    from unittest.mock import MagicMock

    from ontosql.compile.execute import _inserted_identity

    plan = compile_save_plan(PersonMap, Person(id=5, name="A", employer=None), is_new=True)
    result = MagicMock(inserted_primary_key=())
    assert _inserted_identity(result, plan, {"id": 5, "name": "A"}) == 5
