"""Sync/async session parity — same scenarios through both session types."""

from __future__ import annotations

import pytest

from ontosql import AsyncOntoSession, OntoSession
from tests.models import OrganizationMap, Person, PersonMap

pytestmark = pytest.mark.parametrize("session_factory", ["sync", "async"])


@pytest.fixture
async def parity_session(session_factory: str, sync_engine, async_engine):
    if session_factory == "sync":
        with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
            yield session
    else:
        async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
            yield session


async def _get(session, entity_type, *, identity):
    if isinstance(session, AsyncOntoSession):
        return await session.get(entity_type, identity=identity)
    return session.get(entity_type, identity=identity)


async def _save(session, instance, *, flush_now: bool = True):
    if isinstance(session, AsyncOntoSession):
        return await session.save(instance, flush_now=flush_now)
    return session.save(instance, flush_now=flush_now)


async def _delete(session, instance):
    if isinstance(session, AsyncOntoSession):
        return await session.delete(instance)
    return session.delete(instance)


@pytest.mark.asyncio
async def test_parity_get_and_save_roundtrip(parity_session) -> None:
    session = parity_session
    person = await _get(session, Person, identity=1)
    assert person is not None
    assert person.name == "Ada Lovelace"

    person.name = "Ada L."
    saved = await _save(session, person)
    assert saved.name == "Ada L."

    reloaded = await _get(session, Person, identity=1)
    assert reloaded is not None
    assert reloaded.name == "Ada L."


async def _flush(session):
    if isinstance(session, AsyncOntoSession):
        return await session.flush()
    return session.flush()


@pytest.mark.asyncio
async def test_parity_deferred_flush(parity_session) -> None:
    session = parity_session
    created = await _save(
        session,
        Person.model_construct(id=None, name="Deferred", employer=None),
        flush_now=False,
    )
    assert created.id is None
    await _flush(session)
    assert created.id is not None
    reloaded = await _get(session, Person, identity=created.id)
    assert reloaded is not None
    assert reloaded.name == "Deferred"


@pytest.mark.asyncio
async def test_parity_mapper_metadata(session_factory: str) -> None:
    meta = PersonMap.metadata()
    assert meta.entity is Person
    assert "name" in meta.column_field_names()


@pytest.mark.asyncio
async def test_parity_create_and_delete(parity_session) -> None:
    session = parity_session
    created = await _save(session, Person(id=500, name="Parity Test", employer=None))
    assert created.id == 500

    loaded = await _get(session, Person, identity=500)
    assert loaded is not None
    assert loaded.name == "Parity Test"

    await _delete(session, loaded)
    assert await _get(session, Person, identity=500) is None
