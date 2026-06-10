"""Synchronous OntoSession."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from ontosql.compile.select import compile_select_plan
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.base import SessionBase
from ontosql.session.hydrate import hydrate_first, hydrate_row


class OntoSession(SessionBase):
    """Synchronous unit of work for semantic CRUD over SQL."""

    def __init__(
        self,
        engine: Engine,
        maps: list[type[Any]] | None = None,
        *,
        registry: MapperRegistry | None = None,
    ) -> None:
        super().__init__(maps, registry=registry)
        self._engine = engine
        self._session = Session(engine)
        self._owns_commit = True

    def __enter__(self) -> OntoSession:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
        self._session.close()

    def create_tables(self, *models: type[SQLModel]) -> None:
        """Create physical tables (convenience for tests)."""
        SQLModel.metadata.create_all(self._engine, tables=[m.__table__ for m in models])  # type: ignore[attr-defined]

    def get(
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
        return hydrate_first(plan, self._session.exec(plan.select))

    def find(
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
        rows = self._session.exec(plan.select).all()
        return [hydrate_row(plan, row) for row in rows]

    def execute_sql(self, statement: str, params: dict[str, Any] | None = None) -> Any:
        """Execute raw SQL and return the result."""
        from sqlalchemy import text

        return self._session.exec(text(statement), params=params or {})
