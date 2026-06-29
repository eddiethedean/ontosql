"""Tests for write/delete plan execution."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel, create_engine

from ontosql import Map, OntoMapper
from ontosql.compile.execute import (
    ExecuteError,
    _update_identity,
    async_execute_delete_plan,
    async_execute_write_plan,
    execute_delete_plan,
    execute_write_plan,
)
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.compile.write import WriteCompileError, compile_delete_plan, compile_save_plan
from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.registry import MapperRegistry
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow
from tests.models_m2m import (
    M2MPersonRow,
    PersonSkillRow,
    Skill,
    SkilledPerson,
    SkilledPersonMap,
    SkillRow,
)


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


def test_execute_insert_and_update(sync_engine) -> None:
    with Session(sync_engine) as session:
        person = Person(id=70, name="Exec", employer=None)
        plan = compile_save_plan(PersonMap, person, is_new=True)
        assert execute_write_plan(session, plan) == 70
        session.commit()

    with Session(sync_engine) as session:
        row = session.get(PersonRow, 70)
        assert row is not None
        assert row.name == "Exec"

        person.name = "Exec2"
        update_plan = compile_save_plan(PersonMap, person, partial_fields={"name"})
        assert execute_write_plan(session, update_plan) == 70
        session.commit()

    with Session(sync_engine) as session:
        assert session.get(PersonRow, 70).name == "Exec2"
        delete_plan = compile_delete_plan(PersonMap, person)
        execute_delete_plan(session, delete_plan)
        session.commit()
        assert session.get(PersonRow, 70) is None


def test_execute_delete_requires_where(sync_engine) -> None:
    plan = DeletePlan(
        mapper_cls=PersonMap,
        root=TableWrite(table=PersonRow.__table__, where=None),
    )
    with Session(sync_engine) as session, pytest.raises(ExecuteError, match="where clause"):
        execute_delete_plan(session, plan)


def test_update_identity_without_where() -> None:
    plan = WritePlan(
        mapper_cls=PersonMap,
        operation="update",
        root=TableWrite(table=PersonRow.__table__, values={}, where=None),
        nested=[],
        fk_updates={},
    )
    assert _update_identity(plan) is None


def test_execute_empty_update_no_op(sync_engine) -> None:
    with Session(sync_engine) as session:
        session.add(PersonRow(id=71, name="Keep", org_id=None))
        session.commit()
        empty_update = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(
                table=PersonRow.__table__,
                values={},
                where={"id": 71},
            ),
            nested=[],
            fk_updates={},
        )
        execute_write_plan(session, empty_update)
        row = session.get(PersonRow, 71)
        assert row is not None
        assert row.name == "Keep"


def test_execute_replace_deletes_old_nested(sync_engine) -> None:
    mapper = _replace_person_map()
    with Session(sync_engine) as session:
        row = session.get(PersonRow, 2)
        assert row is not None
        row.org_id = None
        session.commit()
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
    with Session(sync_engine) as session:
        registry = MapperRegistry()
        registry.register(mapper)
        registry.register(OrganizationMap)
        execute_write_plan(session, plan, mapper_registry=registry)
        session.commit()
    with Session(sync_engine) as session:
        assert session.get(OrgRow, 10) is None
        row = session.get(PersonRow, 1)
        assert row is not None
        assert row.org_id is not None
        new_org = session.get(OrgRow, row.org_id)
        assert new_org is not None
        assert new_org.name == "New Org"


def test_execute_replace_shared_nested_raises(sync_engine) -> None:
    mapper = _replace_person_map()
    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=99, name="Steal Org"),
    )
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Shared Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    with Session(sync_engine) as session, pytest.raises(ExecuteError, match="still referenced"):
        registry = MapperRegistry()
        registry.register(mapper)
        registry.register(OrganizationMap)
        execute_write_plan(session, plan, mapper_registry=registry)


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


def test_execute_collection_link_writes_bridge(m2m_engine) -> None:
    person = SkilledPerson(id=1, name="Ada", skills=[Skill(id=10, name="SQL")])
    plan = compile_save_plan(SkilledPersonMap, person, partial_fields={"skills"})
    with Session(m2m_engine) as session:
        execute_write_plan(session, plan)
        session.commit()
    with Session(m2m_engine) as session:
        links = session.exec(select(PersonSkillRow)).scalars().all()
        assert len(links) == 1
        assert links[0].person_id == 1
        assert links[0].skill_id == 10


def test_compile_collection_link_requires_identity() -> None:
    person = SkilledPerson(id=1, name="Ada", skills=[Skill.model_construct(name="No Id", id=None)])
    with pytest.raises(WriteCompileError, match="requires an identity"):
        compile_save_plan(SkilledPersonMap, person, partial_fields={"skills"})


@pytest.mark.asyncio
async def test_async_execute_plans() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        person = Person(id=80, name="Async", employer=None)
        plan = compile_save_plan(PersonMap, person, is_new=True)
        assert await async_execute_write_plan(session, plan) == 80
        await session.commit()
        delete_plan = compile_delete_plan(PersonMap, person)
        await async_execute_delete_plan(session, delete_plan)
        await session.commit()
    async with AsyncSession(engine) as session:
        row = await session.get(PersonRow, 80)
        assert row is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_async_execute_delete_requires_where() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    plan = DeletePlan(
        mapper_cls=PersonMap,
        root=TableWrite(table=PersonRow.__table__, where=None),
    )
    async with AsyncSession(engine) as session:
        with pytest.raises(ExecuteError, match="where clause"):
            await async_execute_delete_plan(session, plan)
    await engine.dispose()


def test_inserted_identity_no_column_map() -> None:
    from unittest.mock import MagicMock

    from ontosql.compile.execute import _inserted_identity

    plan = MagicMock()
    plan.mapper_cls.identity_field = "id"
    plan.mapper_cls.column_maps = {}
    result = MagicMock(inserted_primary_key=())
    assert _inserted_identity(result, plan, {}) is None
