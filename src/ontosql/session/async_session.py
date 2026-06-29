"""Asynchronous AsyncOntoSession."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ontosql.compile.execute import async_execute_delete_plan, async_execute_write_plan
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.select import compile_count_statement, compile_select_plan
from ontosql.compile.write import compile_delete_plan
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session._ops import (
    compile_save_plan_for_instance,
    count_scalar,
    identity_from_write_plan,
    reload_identity,
    resolve_save_is_new_and_snapshot,
    validate_get_identity,
)
from ontosql.session.base import SessionBase
from ontosql.session.collections import attach_collections_async
from ontosql.session.graph_sync import flush_graph_sync, queue_graph_push, queue_graph_remove
from ontosql.session.hydrate import hydrate_first, hydrate_row
from ontosql.session.state import PendingDelete
from ontosql.sync.graph import GraphSyncMode


class AsyncOntoSession(SessionBase):
    """Async unit of work for semantic CRUD over SQL."""

    def __init__(
        self,
        engine: AsyncEngine,
        maps: list[type[Any]] | None = None,
        *,
        registry: MapperRegistry | None = None,
        graph_sync: Any | None = None,
        graph_sync_mode: GraphSyncMode = "patch",
    ) -> None:
        super().__init__(maps, registry=registry)
        self._engine = engine
        self._maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._session: AsyncSession | None = None
        self._graph_sync = graph_sync
        self._graph_sync_mode = graph_sync_mode

    async def __aenter__(self) -> AsyncOntoSession:
        self._session = self._maker()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                if self._state.pending:
                    await self.flush()
                await self._session.commit()
                flush_graph_sync(
                    self._state,
                    self._graph_sync,
                    mode=self._graph_sync_mode,
                    mapper_for=self._mapper_for,
                )
            else:
                self._state.clear_graph_sync()
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("AsyncOntoSession is not active; use 'async with'")
        return self._session

    def _register(self, instance: OntoModel) -> OntoModel:
        self._state.register(instance)
        return instance

    async def get(
        self,
        entity_type: type[OntoModel],
        *,
        id: Any | None = None,
        iri: str | None = None,
    ) -> OntoModel | None:
        validate_get_identity(id=id, iri=iri)
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
        result = await self._require_session().execute(plan.select)
        instance = hydrate_first(plan, result)
        if instance is None:
            return None
        await attach_collections_async(self._require_session(), mapper_cls, [instance])
        return self._register(instance)

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
        instances = [hydrate_row(plan, row) for row in result.all()]
        await attach_collections_async(self._require_session(), mapper_cls, instances)
        return [self._register(inst) for inst in instances]

    async def count(
        self,
        entity_type: type[OntoModel],
        *,
        where: Any | None = None,
    ) -> int:
        mapper_cls = self._mapper_for(entity_type)
        stmt = compile_count_statement(mapper_cls, where=where)
        result = await self._require_session().execute(stmt)
        row = result.one()
        return count_scalar(row)

    async def _reload_after_save(
        self,
        instance: OntoModel,
        mapper_cls: type[Any],
        plan: WritePlan,
        inserted_id: Any,
    ) -> OntoModel:
        identity = reload_identity(instance, mapper_cls, plan, inserted_id)
        if identity is not None:
            reloaded = await self.get(type(instance), id=identity)
            if reloaded is not None:
                return reloaded
        return instance

    async def _queue_graph_sync_after_save(
        self,
        instance: OntoModel,
        mapper_cls: type[Any],
        plan: WritePlan,
        inserted_id: Any,
    ) -> OntoModel:
        reloaded = await self._reload_after_save(instance, mapper_cls, plan, inserted_id)
        if self._graph_sync is not None:
            queue_graph_push(self._state, reloaded)
        return reloaded

    async def _load_snapshot_from_db(
        self, instance: OntoModel, mapper_cls: type[Any]
    ) -> dict[str, Any] | None:
        identity = getattr(instance, mapper_cls.identity_field, None)
        if identity is None:
            return None
        plan = compile_select_plan(mapper_cls, id_value=identity, limit=1)
        result = await self._require_session().execute(plan.select)
        row_instance = hydrate_first(plan, result)
        if row_instance is None:
            return None
        return row_instance.model_dump()

    async def save(self, instance: OntoModel, *, flush: bool = True) -> OntoModel:
        mapper_cls = self._mapper_for(type(instance))
        is_new = self._is_new_instance(mapper_cls, instance)
        db_snapshot = await self._load_snapshot_from_db(instance, mapper_cls)
        is_new, snapshot = resolve_save_is_new_and_snapshot(
            self._state,
            instance,
            is_new=is_new,
            db_snapshot=db_snapshot,
        )
        plan = compile_save_plan_for_instance(
            mapper_cls, instance, is_new=is_new, snapshot=snapshot
        )
        if flush:
            inserted_id = await self._execute_write(plan)
            return await self._queue_graph_sync_after_save(instance, mapper_cls, plan, inserted_id)
        self._state.pending.append(plan)
        return instance

    async def delete(self, instance: OntoModel, *, flush: bool = True) -> None:
        mapper_cls = self._mapper_for(type(instance))
        plan = compile_delete_plan(mapper_cls, instance)
        if flush:
            await self._execute_delete(plan)
            if self._graph_sync is not None:
                queue_graph_remove(self._state, instance)
        else:
            self._state.pending.append(PendingDelete(plan=plan, instance=instance))

    async def _apply_pending_delete(self, pending: PendingDelete) -> None:
        await async_execute_delete_plan(self._require_session(), pending.plan)
        mapper_cls = pending.plan.mapper_cls
        identity = getattr(pending.instance, mapper_cls.identity_field, None)
        if identity is not None:
            self._state.expire(mapper_cls.entity, identity)
        if self._graph_sync is not None:
            queue_graph_remove(self._state, pending.instance)

    async def flush(self) -> None:
        pending = list(self._state.pending)
        self._state.clear_pending()
        for item in pending:
            if isinstance(item, WritePlan):
                plan = item
                inserted_id = await self._execute_write(plan)
                entity_type = plan.mapper_cls.entity
                identity = identity_from_write_plan(plan, inserted_id)
                if identity is not None and self._graph_sync is not None:
                    reloaded = await self.get(entity_type, id=identity)
                    if reloaded is not None:
                        queue_graph_push(self._state, reloaded)
            elif isinstance(item, PendingDelete):
                await self._apply_pending_delete(item)

    async def _execute_write(self, plan: WritePlan) -> Any:
        session = self._require_session()
        returned = await async_execute_write_plan(session, plan)
        identity = identity_from_write_plan(plan, returned)
        if identity is not None:
            self._state.expire(plan.mapper_cls.entity, identity)
        return identity

    async def _execute_delete(self, plan: DeletePlan) -> None:
        await async_execute_delete_plan(self._require_session(), plan)
        if plan.root.where:
            identity = next(iter(plan.root.where.values()))
            self._state.expire(plan.mapper_cls.entity, identity)

    async def execute_sql(self, statement: str, params: dict[str, Any] | None = None) -> Any:
        from sqlalchemy import text

        return await self._require_session().execute(text(statement), params or {})
