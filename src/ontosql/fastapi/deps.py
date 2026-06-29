"""FastAPI dependency helpers for OntoSQL sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from ontosql.session.async_session import AsyncOntoSession
from ontosql.session.sync import OntoSession


def onto_session_lifespan(app: FastAPI, engine: Engine, maps: list[type[Any]]) -> None:
    """Store engine and maps on app.state for sync session dependencies."""
    app.state.onto_engine = engine
    app.state.onto_maps = maps
    app.state.onto_async_engine = None


def onto_async_session_lifespan(app: FastAPI, engine: AsyncEngine, maps: list[type[Any]]) -> None:
    """Store async engine and maps on app.state for AsyncSessionDep."""
    app.state.onto_async_engine = engine
    app.state.onto_maps = maps
    app.state.onto_engine = None


@contextmanager
def _sync_session(engine: Engine, maps: list[type[Any]]) -> Iterator[OntoSession]:
    with OntoSession(engine, maps=maps) as session:
        yield session


@asynccontextmanager
async def _async_session(
    engine: AsyncEngine, maps: list[type[Any]]
) -> AsyncIterator[AsyncOntoSession]:
    async with AsyncOntoSession(engine, maps=maps) as session:
        yield session


def get_onto_session(request: Request) -> Iterator[OntoSession]:
    """Yield a synchronous OntoSession bound to app.state engine and maps."""
    engine: Engine = request.app.state.onto_engine
    maps: list[type[Any]] = request.app.state.onto_maps
    with _sync_session(engine, maps) as session:
        yield session


async def get_async_onto_session(request: Request) -> AsyncIterator[AsyncOntoSession]:
    """Yield an AsyncOntoSession bound to app.state async engine and maps."""
    engine: AsyncEngine | None = getattr(request.app.state, "onto_async_engine", None)
    if engine is None:
        fallback = getattr(request.app.state, "onto_engine", None)
        if isinstance(fallback, AsyncEngine):
            engine = fallback
    if engine is None:
        raise RuntimeError(
            "app.state.onto_async_engine is missing; "
            "call onto_async_session_lifespan(app, engine, maps)"
        )
    maps: list[type[Any]] = request.app.state.onto_maps
    async with _async_session(engine, maps) as session:
        yield session


SessionDep = Annotated[OntoSession, Depends(get_onto_session)]
AsyncSessionDep = Annotated[AsyncOntoSession, Depends(get_async_onto_session)]
