"""Integration tests for AsyncOntoSession save/delete."""

from __future__ import annotations

import pytest

from tests.models import Person


@pytest.mark.asyncio
async def test_async_save_insert(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from tests.models import OrganizationMap, PersonMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = Person(id=50, name="Async Person", employer=None)
        saved = await session.save(person)
        assert saved.id == 50
        loaded = await session.get(Person, identity=50)
        assert loaded is not None
        assert loaded.name == "Async Person"


@pytest.mark.asyncio
async def test_async_graph_sync_on_save(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from ontosql.sync import StoreSyncTarget
    from tests.conftest import graph_literal_values
    from tests.models import OrganizationMap, PersonMap

    target = StoreSyncTarget()
    async with AsyncOntoSession(
        async_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    ) as session:
        person = Person(id=55, name="Async Sync", employer=None)
        await session.save(person)
    names = graph_literal_values(target.graph, "https://data.example.org/person/55", "schema:name")
    assert names == ["Async Sync"]


@pytest.mark.asyncio
async def test_async_delete_person(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from tests.models import OrganizationMap, PersonMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = await session.get(Person, identity=2)
        assert person is not None
        await session.delete(person)
        assert await session.get(Person, identity=2) is None


@pytest.mark.asyncio
async def test_async_rollback_discards_uncommitted_write(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from tests.models import OrganizationMap, PersonMap

    with pytest.raises(RuntimeError, match="abort"):
        async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
            await session.save(Person(id=501, name="Should Not Persist", employer=None))
            raise RuntimeError("abort")
    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        assert await session.get(Person, identity=501) is None
