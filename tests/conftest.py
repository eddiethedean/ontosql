"""Pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from pyoxigraph import NamedNode
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from triplemodel import Store

from ontosql import AsyncOntoSession, OntoSession
from ontosql.registry import PrefixRegistry
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def graph_literal_values(
    graph: Store,
    subject_iri: str,
    predicate_curie: str,
    *,
    registry: PrefixRegistry | None = None,
) -> list[str]:
    """Return literal values for a subject/predicate in a TripleModel Store."""
    reg = registry or PrefixRegistry()
    subject = NamedNode(subject_iri)
    predicate = NamedNode(reg.expand(predicate_curie))
    return [str(getattr(obj, "value", obj)) for obj in graph.objects(subject, predicate)]


def graph_object_iris(
    graph: Store,
    subject_iri: str,
    predicate_curie: str,
    *,
    registry: PrefixRegistry | None = None,
) -> list[str]:
    """Return object IRIs (NamedNode.value) for a subject/predicate."""
    reg = registry or PrefixRegistry()
    subject = NamedNode(subject_iri)
    predicate = NamedNode(reg.expand(predicate_curie))
    return [str(obj.value) for obj in graph.objects(subject, predicate)]


@pytest.fixture
def sync_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(OrgRow(id=10, name="Analytical Engines Inc."))
        session.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        session.add(PersonRow(id=2, name="Charles Babbage", org_id=10))
        session.add(PersonRow(id=3, name="Solo Person", org_id=None))
        session.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def onto_session(sync_engine):
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        yield session


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        session.add(OrgRow(id=10, name="Analytical Engines Inc."))
        session.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        session.add(PersonRow(id=2, name="Charles Babbage", org_id=10))
        await session.commit()
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_onto_session(async_engine):
    async with AsyncOntoSession(async_engine, maps=[PersonMap, OrganizationMap]) as session:
        yield session


@pytest.fixture
def person() -> Person:
    return Person(
        id=1,
        name="Ada Lovelace",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )


@pytest.fixture
def organization() -> Organization:
    return Organization(id=10, name="Analytical Engines Inc.")


def build_async_onto_test_app(
    *,
    maps: list | None = None,
    entities: tuple | None = None,
    router_kwargs: dict | None = None,
) -> Any:
    """Build a FastAPI app with async OntoRouter for integration tests."""
    pytest.importorskip("fastapi")
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from ontosql.fastapi.deps import onto_async_session_lifespan
    from ontosql.fastapi.router import OntoRouter

    resolved_maps = maps if maps is not None else [PersonMap, OrganizationMap]
    resolved_entities = entities if entities is not None else (Person, Organization)
    resolved_router_kwargs = router_kwargs if router_kwargs is not None else {}

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    def _seed(connection: Any) -> None:
        with Session(bind=connection) as raw:
            raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
            raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
            raw.commit()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await conn.run_sync(_seed)
        onto_async_session_lifespan(app, engine, resolved_maps)
        yield
        await engine.dispose()

    app = FastAPI(lifespan=lifespan)

    router = OntoRouter(maps=resolved_maps, **resolved_router_kwargs)
    for entity in resolved_entities:
        router.register(entity)
    router.include_in(app)
    return app
