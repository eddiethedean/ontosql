"""Integration tests for AsyncOntoSession."""

from __future__ import annotations

import pytest

from tests.models import Person


@pytest.mark.asyncio
async def test_async_get(async_onto_session) -> None:
    person = await async_onto_session.get(Person, identity=1)
    assert person is not None
    assert person.name == "Ada Lovelace"
    assert person.employer is not None
    assert person.employer.name == "Analytical Engines Inc."


@pytest.mark.asyncio
async def test_async_get_missing(async_onto_session) -> None:
    assert await async_onto_session.get(Person, identity=999) is None


@pytest.mark.asyncio
async def test_async_find(async_onto_session) -> None:
    results = await async_onto_session.find(Person, where=Person.name.startswith("C"))
    assert len(results) == 1
    assert results[0].name == "Charles Babbage"


@pytest.mark.asyncio
async def test_async_save_partial_update(async_engine) -> None:
    from ontosql import AsyncOntoSession
    from tests.models import OrganizationMap, PersonMap

    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = await session.get(Person, identity=1)
        assert person is not None
        person.name = "Ada Updated"
        await session.save(person)
        reloaded = await session.get(Person, identity=1)
        assert reloaded is not None
        assert reloaded.name == "Ada Updated"
        assert reloaded.employer is not None
        assert reloaded.employer.name == "Analytical Engines Inc."


@pytest.mark.asyncio
async def test_async_identity_map(async_onto_session) -> None:
    first = await async_onto_session.get(Person, identity=1)
    second = await async_onto_session.get(Person, identity=1)
    assert first is second
