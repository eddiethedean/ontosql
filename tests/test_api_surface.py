"""Tests for public API naming."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from ontosql.sync import materialize_find_async
from tests.models import OrganizationMap, Person, PersonMap


def test_get_identity(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        person = session.get(Person, identity=1)
        assert person is not None
        assert person.name == "Ada Lovelace"


def test_save_flush_now_deferred(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        session.save(Person(id=88, name="Deferred", employer=None), flush_now=False)
        assert session.get(Person, identity=88) is None
        session.flush()
        assert session.get(Person, identity=88) is not None


def test_clear_pending(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        session.save(Person(id=89, name="Clear", employer=None), flush_now=False)
        session.clear_pending()
        assert session.get(Person, identity=89) is None


def test_import_mapper_param() -> None:
    from ontosql.import_ import import_from_jsonld

    person = Person(id=1, name="Ada", employer=None)
    doc = person.to_jsonld()
    restored = import_from_jsonld(doc, PersonMap)
    assert restored.name == "Ada"


@pytest.mark.asyncio
async def test_materialize_find_async(async_onto_session) -> None:
    graph = await materialize_find_async(async_onto_session, Person, limit=10)
    assert len(graph) > 0
