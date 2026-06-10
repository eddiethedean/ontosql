"""Edge-case integration tests for sync/async session save/delete paths."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from ontosql.query.expr import FieldPath
from tests.models import Person, PersonMap


@pytest.mark.asyncio
async def test_async_save_pending_queue(async_onto_session) -> None:
    person = Person(id=201, name="Queued", employer=None)
    await async_onto_session.save(person, flush=False)
    assert async_onto_session._state.pending
    async_onto_session.rollback_pending()


def test_field_path_private_attr_raises() -> None:
    path = FieldPath(Person, ("name",))
    with pytest.raises(AttributeError):
        FieldPath.__getattr__(path, "_hidden")
    with pytest.raises(AttributeError):
        _ = path._private  # noqa: SLF001
    with pytest.raises(AttributeError):
        _ = Person.name._private  # noqa: SLF001


def test_delete_and_flush_pending(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, id=1)
        assert person is not None
        session.delete(person, flush=False)
        session.flush()
        assert session.get(Person, id=1) is None


@pytest.mark.asyncio
async def test_async_delete_and_flush_pending(async_onto_session) -> None:
    person = await async_onto_session.get(Person, id=2)
    assert person is not None
    await async_onto_session.delete(person, flush=False)
    await async_onto_session.flush()
    assert await async_onto_session.get(Person, id=2) is None


def test_sync_delete_immediate(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = session.get(Person, id=3)
        assert person is not None
        session.delete(person)
        assert session.get(Person, id=3) is None


def test_sync_flush_write_only(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=98, name="FlushWrite", employer=None), flush=False)
        session.flush()
        assert session.get(Person, id=98) is not None


@pytest.mark.asyncio
async def test_async_count_with_filter(async_onto_session) -> None:
    total = await async_onto_session.count(Person)
    assert total == 2
    filtered = await async_onto_session.count(Person, where=Person.name.startswith("A"))
    assert filtered == 1
