"""Tests for write/delete plan execution."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel

from ontosql.compile.execute import (
    ExecuteError,
    _update_identity,
    async_execute_delete_plan,
    async_execute_write_plan,
    execute_delete_plan,
    execute_write_plan,
)
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.compile.write import compile_delete_plan, compile_save_plan
from tests.models import Person, PersonMap, PersonRow


def test_execute_insert_and_update(sync_engine) -> None:
    with Session(sync_engine) as session:
        person = Person(id=70, name="Exec", employer=None)
        plan = compile_save_plan(PersonMap, person, is_new=True)
        assert execute_write_plan(session, plan) == 70

        person.name = "Exec2"
        update_plan = compile_save_plan(PersonMap, person, partial_fields={"name"})
        assert execute_write_plan(session, update_plan) == 70

        delete_plan = compile_delete_plan(PersonMap, person)
        execute_delete_plan(session, delete_plan)


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
