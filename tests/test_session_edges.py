"""Edge-case coverage for sync/async session save/delete paths."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlmodel import Session

from ontosql import OntoSession
from ontosql.compile.execute import execute_write_plan
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.query.expr import FieldPath
from tests.models import Person, PersonMap, PersonRow


@pytest.mark.asyncio
async def test_async_save_pending_queue(async_onto_session) -> None:
    person = Person(id=201, name="Queued", employer=None)
    await async_onto_session.save(person, flush=False)
    assert async_onto_session._state.pending
    async_onto_session.rollback_pending()


def test_execute_write_values_identity(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        plan = WritePlan(
            mapper_cls=PersonMap,
            operation="insert",
            root=TableWrite(
                table=PersonRow.__table__,
                values={"id": 88, "name": "Val"},
                where=None,
            ),
            nested=[],
            fk_updates={},
        )
        with patch("ontosql.session.sync.execute_write_plan", return_value=None):
            session._execute_write(plan)


def test_execute_update_without_where(sync_engine) -> None:
    with Session(sync_engine) as session:
        plan = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(
                table=PersonRow.__table__,
                values={"name": "NoWhere"},
                where=None,
            ),
            nested=[],
            fk_updates={},
        )
        execute_write_plan(session, plan)


def test_save_where_identity_fallback(sync_engine) -> None:
    plan = WritePlan(
        mapper_cls=PersonMap,
        operation="update",
        root=TableWrite(
            table=PersonRow.__table__,
            values={"name": "WhereId"},
            where={"id": 2},
        ),
        nested=[],
        fk_updates={},
    )
    with (
        OntoSession(sync_engine, maps=[PersonMap]) as session,
        patch("ontosql.session.sync.compile_save_plan", return_value=plan),
        patch("ontosql.session.sync.execute_write_plan", return_value=None),
    ):
        result = session.save(Person.model_construct(name="WhereId", id=None))
        assert result.id == 2


def test_field_path_dunder_getattr() -> None:
    path = FieldPath(Person, ("name",))
    with pytest.raises(AttributeError):
        FieldPath.__getattr__(path, "_hidden")
    with pytest.raises(AttributeError):
        _ = path._private  # noqa: SLF001
    with pytest.raises(AttributeError):
        _ = Person.name._private  # noqa: SLF001


def test_save_returns_instance_without_identity(sync_engine) -> None:
    plan = WritePlan(
        mapper_cls=PersonMap,
        operation="insert",
        root=TableWrite(table=PersonRow.__table__, values={"name": "Orphan"}, where=None),
        nested=[],
        fk_updates={},
    )
    with (
        OntoSession(sync_engine, maps=[PersonMap]) as session,
        patch("ontosql.session.sync.compile_save_plan", return_value=plan),
        patch("ontosql.session.sync.execute_write_plan", return_value=None),
    ):
        person = Person.model_construct(name="Orphan", id=None)
        assert session.save(person) is person


def test_save_identity_from_where(sync_engine) -> None:
    plan = WritePlan(
        mapper_cls=PersonMap,
        operation="update",
        root=TableWrite(
            table=PersonRow.__table__,
            values={"name": "Updated"},
            where={"id": 1},
        ),
        nested=[],
        fk_updates={},
    )
    with (
        OntoSession(sync_engine, maps=[PersonMap]) as session,
        patch("ontosql.session.sync.compile_save_plan", return_value=plan),
        patch("ontosql.session.sync.execute_write_plan", return_value=None),
    ):
        person = Person.model_construct(name="Updated", id=None)
        saved = session.save(person)
        assert saved is not None
        assert saved.id == 1


def test_delete_and_flush_pending(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, id=1)
        assert person is not None
        session.delete(person, flush=False)
        session.flush()


def test_execute_write_identity_branches(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        plan = WritePlan(
            mapper_cls=PersonMap,
            operation="update",
            root=TableWrite(
                table=PersonRow.__table__,
                values={"id": 1, "name": "X"},
                where={"id": 1},
            ),
            nested=[],
            fk_updates={},
        )
        with patch("ontosql.session.sync.execute_write_plan", return_value=None):
            session._execute_write(plan)


@pytest.mark.asyncio
async def test_async_save_and_delete_edges(async_onto_session) -> None:
    plan = WritePlan(
        mapper_cls=PersonMap,
        operation="insert",
        root=TableWrite(table=PersonRow.__table__, values={"name": "AsyncOrphan"}, where=None),
        nested=[],
        fk_updates={},
    )
    with (
        patch("ontosql.session.async_session.compile_save_plan", return_value=plan),
        patch(
            "ontosql.session.async_session.async_execute_write_plan",
            return_value=None,
        ),
    ):
        person = Person.model_construct(name="AsyncOrphan", id=None)
        assert await async_onto_session.save(person) is person

    update_plan = WritePlan(
        mapper_cls=PersonMap,
        operation="update",
        root=TableWrite(
            table=PersonRow.__table__,
            values={"name": "Patched"},
            where={"id": 1},
        ),
        nested=[],
        fk_updates={},
    )
    with (
        patch("ontosql.session.async_session.compile_save_plan", return_value=update_plan),
        patch(
            "ontosql.session.async_session.async_execute_write_plan",
            return_value=None,
        ),
    ):
        saved = await async_onto_session.save(Person.model_construct(name="Patched", id=None))
        assert saved.id == 1

    person = await async_onto_session.get(Person, id=2)
    assert person is not None
    await async_onto_session.delete(person, flush=False)
    await async_onto_session.flush()

    with patch(
        "ontosql.session.async_session.async_execute_write_plan",
        return_value=None,
    ):
        await async_onto_session._execute_write(
            WritePlan(
                mapper_cls=PersonMap,
                operation="insert",
                root=TableWrite(
                    table=PersonRow.__table__,
                    values={"id": 5, "name": "V"},
                    where=None,
                ),
                nested=[],
                fk_updates={},
            )
        )

    await async_onto_session.execute_sql("SELECT 1")


def test_execute_delete_without_where(sync_engine) -> None:
    from ontosql.compile.execute import execute_delete_plan

    plan = DeletePlan(
        mapper_cls=PersonMap,
        root=TableWrite(table=PersonRow.__table__, where=None),
    )
    with Session(sync_engine) as session:
        execute_delete_plan(session, plan)


def test_sync_delete_immediate(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, id=3)
        assert person is not None
        session.delete(person)


def test_sync_flush_write_only(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=98, name="FlushWrite", employer=None), flush=False)
        session.flush()


def test_async_count_scalar_int() -> None:
    from ontosql.session.async_session import _count_scalar

    assert _count_scalar(4) == 4
