"""Synchronous OntoSession."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from ontosql.compile.execute import execute_delete_plan, execute_write_plan
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.select import compile_count_statement, compile_select_plan
from ontosql.compile.write import compile_delete_plan, compile_save_plan
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.base import SessionBase
from ontosql.session.hydrate import hydrate_first, hydrate_row


def _count_scalar(row: Any) -> int:
    if hasattr(row, "_mapping"):
        return int(next(iter(row._mapping.values())))
    if isinstance(row, tuple):
        return int(row[0])
    return int(row)


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

    def _register(self, instance: OntoModel) -> OntoModel:
        self._state.register(instance)
        return instance

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
        if id is not None:
            cached = self._state.get_cached(entity_type, id)
            if cached is not None:
                return cached
        mapper_cls = self._mapper_for(entity_type)
        plan = compile_select_plan(
            mapper_cls,
            id_value=id,
            iri=iri,
            limit=1,
        )
        instance = hydrate_first(plan, self._session.exec(plan.select))
        if instance is None:
            return None
        return self._register(instance)

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
        return [self._register(hydrate_row(plan, row)) for row in rows]

    def count(
        self,
        entity_type: type[OntoModel],
        *,
        where: Any | None = None,
    ) -> int:
        mapper_cls = self._mapper_for(entity_type)
        stmt = compile_count_statement(mapper_cls, where=where)
        result = self._session.exec(stmt).one()
        return _count_scalar(result)

    def save(self, instance: OntoModel, *, flush: bool = True) -> OntoModel:
        mapper_cls = self._mapper_for(type(instance))
        is_new = self._is_new_instance(mapper_cls, instance)
        plan = compile_save_plan(
            mapper_cls,
            instance,
            partial_fields=instance.model_fields_set if not is_new else None,
            is_new=is_new,
        )
        if flush:
            inserted_id = self._execute_write(plan)
            identity = getattr(instance, mapper_cls.identity_field, None)
            if identity is None:
                identity = inserted_id
            if identity is None and plan.root.where:
                identity = next(iter(plan.root.where.values()))  # pragma: no cover
            if identity is not None:
                reloaded = self.get(type(instance), id=identity)
                if reloaded is not None:
                    return reloaded
            return instance
        self._state.pending.append(plan)
        return instance

    def delete(self, instance: OntoModel, *, flush: bool = True) -> None:
        mapper_cls = self._mapper_for(type(instance))
        plan = compile_delete_plan(mapper_cls, instance)
        identity = getattr(instance, mapper_cls.identity_field, None)
        if flush:
            execute_delete_plan(self._session, plan)
            if identity is not None:
                self._state.expire(type(instance), identity)
        else:
            self._state.pending.append(plan)

    def flush(self) -> None:
        """Apply all pending save/delete plans."""
        pending = list(self._state.pending)
        self._state.clear_pending()
        for plan in pending:
            if isinstance(plan, WritePlan):
                self._execute_write(plan)
            elif isinstance(plan, DeletePlan):
                execute_delete_plan(self._session, plan)
                if plan.root.where:
                    identity = next(iter(plan.root.where.values()))
                    self._state.expire(plan.mapper_cls.entity, identity)

    def _execute_write(self, plan: WritePlan) -> Any:
        identity = execute_write_plan(self._session, plan)
        entity_type = plan.mapper_cls.entity
        if identity is None and plan.root.where:
            identity = next(iter(plan.root.where.values()))
        elif identity is None and plan.mapper_cls.identity_field in plan.root.values:
            identity = plan.root.values[plan.mapper_cls.identity_field]
        if identity is not None:
            self._state.expire(entity_type, identity)
        return identity

    def execute_sql(self, statement: str, params: dict[str, Any] | None = None) -> Any:
        """Execute raw SQL and return the result."""
        from sqlalchemy import text

        return self._session.exec(text(statement), params=params or {})
