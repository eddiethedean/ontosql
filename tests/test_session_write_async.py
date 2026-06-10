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
        loaded = await session.get(Person, id=50)
        assert loaded is not None
        assert loaded.name == "Async Person"


@pytest.mark.asyncio
async def test_async_delete(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from tests.models import OrganizationMap, PersonMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = await session.get(Person, id=2)
        assert person is not None
        await session.delete(person)
        assert await session.get(Person, id=2) is None
