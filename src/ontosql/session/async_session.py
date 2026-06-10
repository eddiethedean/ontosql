"""Asynchronous AsyncOntoSession."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ontosql.compile.select import compile_select_plan
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.base import SessionBase
from ontosql.session.hydrate import hydrate_first, hydrate_row


class AsyncOntoSession(SessionBase):
    """Async unit of work for semantic CRUD over SQL."""

    def __init__(
        self,
        engine: AsyncEngine,
        maps: list[type[Any]] | None = None,
        *,
        registry: MapperRegistry | None = None,
    ) -> None:
        super().__init__(maps, registry=registry)
        self._engine = engine
        self._maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncOntoSession:
        self._session = self._maker()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._session is not None
        if exc_type is None:
            await self._session.commit()
        else:
            await self._session.rollback()
        await self._session.close()
        self._session = None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("AsyncOntoSession is not active; use 'async with'")
        return self._session

    async def get(
        self,
        entity_type: type[OntoModel],
        *,
        id: Any | None = None,
        iri: str | None = None,
    ) -> OntoModel | None:
        if id is None and iri is None:
            raise ValueError("get() requires id= or iri=")
        if id is not None and iri is not None:
            raise ValueError("get() accepts only one of id= or iri=")
        mapper_cls = self._mapper_for(entity_type)
        plan = compile_select_plan(
            mapper_cls,
            id_value=id,
            iri=iri,
            limit=1,
        )
        result = await self._require_session().execute(plan.select)
        return hydrate_first(plan, result)

    async def find(
        self,
        entity_type: type[OntoModel],
        *,
        where: Any | None = None,
        order_by: Any | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[OntoModel]:
        mapper_cls = self._mapper_for(entity_type)
        plan = compile_select_plan(
            mapper_cls,
            where=where,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        result = await self._require_session().execute(plan.select)
        return [hydrate_row(plan, row) for row in result.all()]

    async def execute_sql(self, statement: str, params: dict[str, Any] | None = None) -> Any:
        from sqlalchemy import text

        return await self._require_session().execute(text(statement), params or {})
