"""Targeted tests to raise coverage on under-exercised paths."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from pyoxigraph import Literal, NamedNode
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from triplemodel import RDF_TYPE, Store

from ontosql import AsyncOntoSession, Map, OntoMapper, OntoSession
from ontosql.compile.execute import (
    ExecuteError,
    _apply_nested_fk_updates,
    _update_rowcount,
    assert_delete_exclusive,
    async_execute_delete_plan,
    async_execute_write_plan,
    execute_write_plan,
)
from ontosql.compile.plan import CollectionWritePlan, TableWrite, WritePlan
from ontosql.compile.write import compile_delete_plan, compile_save_plan
from ontosql.fastapi.deps import (
    get_async_onto_session,
    get_onto_session,
    onto_session_lifespan,
)
from ontosql.import_.hydrate import (
    OntoImportError,
    _coerce_identity,
    _coerce_literal,
    _expand_datatype,
    _literal_matches_meta,
    _pick_literal,
    graph_to_instance,
)
from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.registry import MapperRegistry
from ontosql.registry import PrefixRegistry
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

pytest.importorskip("fastapi")


@pytest.fixture
def m2m_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(M2MPersonRow(id=1, name="Ada"))
        session.add(SkillRow(id=10, name="SQL"))
        session.commit()
    yield engine
    engine.dispose()


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


def _replace_skills_map() -> type[OntoMapper[SkilledPerson]]:
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
            cascade=CascadePolicy.REPLACE,
        )

    return ReplaceSkillsPersonMap


# --- fastapi.deps ---


def test_onto_session_lifespan_and_get_onto_session(sync_engine) -> None:
    app = FastAPI()
    onto_session_lifespan(app, sync_engine, [PersonMap])
    assert app.state.onto_engine is sync_engine
    assert app.state.onto_maps == [PersonMap]
    assert app.state.onto_async_engine is None

    request = MagicMock()
    request.app = app
    gen = get_onto_session(request)
    session = next(gen)
    assert isinstance(session, OntoSession)
    gen.close()


@pytest.mark.asyncio
async def test_get_async_onto_session_missing_raises() -> None:
    app = FastAPI()
    app.state.onto_maps = [PersonMap]
    request = MagicMock()
    request.app = app
    gen = get_async_onto_session(request)
    with pytest.raises(RuntimeError, match="onto_async_engine"):
        await gen.__anext__()


@pytest.mark.asyncio
async def test_get_async_onto_session_async_engine_fallback(async_engine) -> None:
    app = FastAPI()
    app.state.onto_engine = async_engine
    app.state.onto_maps = [PersonMap]
    request = MagicMock()
    request.app = app
    gen = get_async_onto_session(request)
    async for session in gen:
        assert isinstance(session, AsyncOntoSession)
        break


# --- compile.execute (sync edge cases) ---


def test_update_rowcount_none() -> None:
    assert _update_rowcount(MagicMock(spec=[])) == 0


def test_apply_nested_fk_updates_skips_none() -> None:
    plan = compile_save_plan(PersonMap, Person(id=1, name="A", employer=None), is_new=False)
    fk: dict[str, object] = {}
    _apply_nested_fk_updates(plan, fk, "employer", None)
    assert fk == {}


def test_execute_strict_update_zero_rows(sync_engine) -> None:
    person = Person(id=9999, name="Missing", employer=None)
    plan = compile_save_plan(PersonMap, person, partial_fields={"name"}, is_new=False)
    with Session(sync_engine) as session, pytest.raises(ExecuteError, match="0 rows"):
        execute_write_plan(session, plan, strict_updates=True)


def test_assert_delete_exclusive_requires_registry() -> None:
    plan = compile_delete_plan(PersonMap, Person(id=1, name="A", employer=None))
    with pytest.raises(ExecuteError, match="mapper_registry"):
        assert_delete_exclusive(plan, field_name="x", run_count=lambda _: 0, mapper_registry=None)


def test_execute_insert_collection_without_parent_identity(m2m_engine) -> None:
    from unittest.mock import patch

    cwp = CollectionWritePlan(
        field_name="skills",
        policy=CascadePolicy.LINK,
        items=[Skill(id=10, name="SQL")],
    )
    plan = WritePlan(
        mapper_cls=SkilledPersonMap,
        operation="insert",
        root=TableWrite(table=M2MPersonRow.__table__, values={"name": "NoId"}),
        collections=[cwp],
    )
    with (
        Session(m2m_engine) as session,
        patch("ontosql.compile.execute._inserted_identity", return_value=None),
        pytest.raises(ExecuteError, match="parent identity"),
    ):
        execute_write_plan(session, plan)


def test_execute_collection_link_missing_identity_at_runtime(m2m_engine) -> None:
    cwp = CollectionWritePlan(
        field_name="skills",
        policy=CascadePolicy.LINK,
        items=[Skill.model_construct(id=None, name="SQL")],
    )
    plan = WritePlan(
        mapper_cls=SkilledPersonMap,
        operation="update",
        root=TableWrite(table=M2MPersonRow.__table__, values={}, where={"id": 1}),
        collections=[cwp],
    )
    with (
        Session(m2m_engine) as session,
        pytest.raises(ExecuteError, match="requires nested identity"),
    ):
        execute_write_plan(session, plan)


# --- compile.execute (async paths) ---


@pytest.mark.asyncio
async def test_async_replace_deletes_old_nested() -> None:
    mapper = _replace_person_map()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        session.add(OrgRow(id=10, name="Old Org"))
        session.add(PersonRow(id=1, name="Ada", org_id=10))
        await session.commit()

    person = Person(
        id=1,
        name="Ada",
        employer=Organization.model_construct(id=None, name="New Org"),
    )
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    registry = MapperRegistry()
    registry.register(mapper)
    registry.register(OrganizationMap)
    async with AsyncSession(engine) as session:
        await async_execute_write_plan(session, plan, mapper_registry=registry)
        await session.commit()
    async with AsyncSession(engine) as session:
        assert await session.get(OrgRow, 10) is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_replace_requires_registry() -> None:
    mapper = _replace_person_map()
    person = Person(
        id=1,
        name="Ada",
        employer=Organization.model_construct(id=None, name="New Org"),
    )
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        with pytest.raises(ExecuteError, match="mapper_registry"):
            await async_execute_write_plan(session, plan)
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_delete_cascade_replace_nested() -> None:
    mapper = _replace_person_map()
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        session.add(OrgRow(id=10, name="Org"))
        session.add(PersonRow(id=1, name="Ada", org_id=10))
        await session.commit()

    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Org"))
    plan = compile_delete_plan(mapper, person)
    registry = MapperRegistry()
    registry.register(mapper)
    registry.register(OrganizationMap)
    async with AsyncSession(engine) as session:
        await async_execute_delete_plan(session, plan, mapper_registry=registry)
        await session.commit()
    async with AsyncSession(engine) as session:
        assert await session.get(OrgRow, 10) is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_delete_nested_requires_registry() -> None:
    mapper = _replace_person_map()
    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Org"))
    plan = compile_delete_plan(mapper, person)
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        with pytest.raises(ExecuteError, match="mapper_registry"):
            await async_execute_delete_plan(session, plan)
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_collection_link_writes_bridge() -> None:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(
            lambda c: (
                Session(bind=c).add_all(
                    [
                        M2MPersonRow(id=2, name="Grace"),
                        SkillRow(id=10, name="SQL"),
                    ]
                )
                or Session(bind=c).commit()
            )
        )

    person = SkilledPerson(id=2, name="Grace", skills=[Skill(id=10, name="SQL")])
    plan = compile_save_plan(SkilledPersonMap, person, partial_fields={"skills"})
    async with AsyncSession(engine) as session:
        await async_execute_write_plan(session, plan)
        await session.commit()
    async with AsyncSession(engine) as session:
        from sqlalchemy import select

        links = (await session.execute(select(PersonSkillRow))).scalars().all()
        assert len(links) == 1
        assert links[0].person_id == 2
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_collection_replace_deletes_orphans() -> None:
    mapper = _replace_skills_map()
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    def _seed(connection):
        with Session(bind=connection) as session:
            session.add(M2MPersonRow(id=1, name="Ada"))
            session.add(SkillRow(id=10, name="SQL"))
            session.add(SkillRow(id=11, name="RDF"))
            session.add(SkillRow(id=12, name="SPARQL"))
            session.add(PersonSkillRow(person_id=1, skill_id=10))
            session.add(PersonSkillRow(person_id=1, skill_id=11))
            session.commit()

    async with engine.begin() as conn:
        await conn.run_sync(_seed)

    person = SkilledPerson(id=1, name="Ada", skills=[Skill(id=12, name="SPARQL")])
    snapshot = {
        "id": 1,
        "name": "Ada",
        "skills": [{"id": 10, "name": "SQL"}, {"id": 11, "name": "RDF"}],
    }
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"skills"},
        is_new=False,
        snapshot=snapshot,
    )
    registry = MapperRegistry()
    registry.register(mapper)
    registry.register(SkillMap)
    async with AsyncSession(engine) as session:
        await async_execute_write_plan(session, plan, mapper_registry=registry)
        await session.commit()
    async with AsyncSession(engine) as session:
        assert await session.get(SkillRow, 10) is None
        assert await session.get(SkillRow, 11) is None
        assert await session.get(SkillRow, 12) is not None
    await engine.dispose()


# --- import_.hydrate ---


def test_expand_datatype_prefix() -> None:
    reg = PrefixRegistry({"xsd": "http://www.w3.org/2001/XMLSchema#"})
    assert (
        _expand_datatype({"datatype": "xsd:integer"}, reg)
        == "http://www.w3.org/2001/XMLSchema#integer"
    )


def test_literal_matches_meta_language() -> None:
    reg = PrefixRegistry()
    lit = Literal("hello", language="en")
    assert _literal_matches_meta(lit, {"language": "en"}, reg) is True
    assert _literal_matches_meta(lit, {"language": "fr"}, reg) is False


def test_pick_literal_no_match_raises() -> None:
    reg = PrefixRegistry()
    lit = Literal("hello", language="en")
    with pytest.raises(OntoImportError, match="No literal matches"):
        _pick_literal([lit], {"language": "fr"}, reg)


def test_coerce_literal_named_node_and_invalid_bool() -> None:
    reg = PrefixRegistry()
    node_value = _coerce_literal(NamedNode("http://ex/x"), py_type=str, registry=reg, meta={})
    assert "http://ex/x" in node_value
    with pytest.raises(OntoImportError, match="bool"):
        _coerce_literal(Literal("maybe"), py_type=bool, registry=reg, meta={})


def test_coerce_literal_int_and_datatype_mismatch() -> None:
    reg = PrefixRegistry()
    with pytest.raises(OntoImportError, match="int"):
        _coerce_literal(Literal("not-a-number"), py_type=int, registry=reg, meta={})
    with pytest.raises(OntoImportError, match="datatype"):
        _coerce_literal(
            Literal("1", datatype=NamedNode("http://www.w3.org/2001/XMLSchema#string")),
            py_type=str,
            registry=reg,
            meta={"datatype": "http://www.w3.org/2001/XMLSchema#integer"},
        )


def test_coerce_identity_from_literal() -> None:
    value = _coerce_identity(Literal("7"), Person, registry=PrefixRegistry())
    assert value == 7


def test_import_scalar_multiple_values_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("A")))
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("B")))
    with pytest.raises(OntoImportError, match="Scalar field"):
        graph_to_instance(graph, PersonMap, iri="https://data.example.org/person/1")


def test_import_nested_wrong_term_type_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("Ada")))
    graph.add((subject, NamedNode("https://schema.org/worksFor"), Literal("bad")))
    with pytest.raises(OntoImportError, match="URI object"):
        graph_to_instance(graph, PersonMap, iri="https://data.example.org/person/1")


def test_import_collection_non_uri_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("Ada")))
    graph.add((subject, NamedNode("https://schema.org/knowsAbout"), Literal("not-uri")))

    class CollPersonMap(OntoMapper[SkilledPerson]):
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

    with pytest.raises(OntoImportError, match="URI objects"):
        graph_to_instance(graph, CollPersonMap, iri="https://data.example.org/person/1")


def test_import_max_nesting_depth_exceeded() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    org = NamedNode("https://data.example.org/org/10")
    graph.add((subject, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Person")))
    graph.add((org, NamedNode(RDF_TYPE), NamedNode("https://schema.org/Organization")))
    graph.add((subject, NamedNode("https://schema.org/name"), Literal("Ada")))
    graph.add((org, NamedNode("https://schema.org/name"), Literal("Org")))
    graph.add((subject, NamedNode("https://schema.org/worksFor"), org))
    with pytest.raises(OntoImportError, match="max_nesting_depth"):
        graph_to_instance(
            graph,
            PersonMap,
            iri="https://data.example.org/person/1",
            max_nesting_depth=0,
        )


# --- async_session ---


@pytest.mark.asyncio
async def test_async_deferred_flush_and_rollback_warn(async_engine) -> None:
    from tests.models import OrganizationMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        await session.save(Person(id=600, name="Deferred", employer=None), flush_now=False)
        assert session._state.pending  # noqa: SLF001
        with pytest.warns(UserWarning, match="clear_uow=False"):
            await session.rollback(clear_uow=False)


@pytest.mark.asyncio
async def test_async_get_by_iri_and_pending_delete(async_engine) -> None:
    from tests.models import OrganizationMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = await session.get(Person, iri="https://data.example.org/person/1")
        assert person is not None
        assert person.name == "Ada Lovelace"
        await session.delete(person, flush_now=False)
        assert await session.get(Person, identity=1) is None
        assert await session.count(Person) == 1


@pytest.mark.asyncio
async def test_async_exit_auto_flushes_pending(async_engine) -> None:
    from tests.models import OrganizationMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        await session.save(Person(id=601, name="AutoFlush", employer=None), flush_now=False)
    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        loaded = await session.get(Person, identity=601)
        assert loaded is not None
        assert loaded.name == "AutoFlush"


def test_session_state_identity_collision_warns() -> None:
    from ontosql.session.state import SessionState

    state = SessionState()
    a = Person(id=1, name="A", employer=None)
    b = Person(id=1, name="B", employer=None)
    state.register(a)
    with pytest.warns(UserWarning, match="replaced"):
        state.register(b)
