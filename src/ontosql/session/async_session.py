"""Asynchronous AsyncOntoSession."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ontosql._log import logger
from ontosql.compile.execute import async_execute_delete_plan, async_execute_write_plan
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.select import compile_count_statement, compile_select_plan
from ontosql.compile.write import compile_delete_plan, count_scalar
from ontosql.semantic.model import OntoModel
from ontosql.session._ops import (
    compile_save_plan_for_instance,
    identity_from_write_plan,
    resolve_save_is_new_and_snapshot,
    validate_get_identity,
)
from ontosql.session._sql import async_load_snapshot_from_db, async_reload_after_save
from ontosql.session.base import GraphSyncTargetLike, SessionBase
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
        graph_sync: GraphSyncTargetLike | None = None,
        graph_sync_mode: GraphSyncMode = "patch",
    ) -> None:
        super().__init__(maps)
        self._engine = engine
        self._maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._session: AsyncSession | None = None
        self._graph_sync = graph_sync
        self._graph_sync_mode = graph_sync_mode

    async def __aenter__(self) -> AsyncOntoSession:
        self._session = self._maker()
        logger.debug("session open async")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                if self._state.pending:
                    await self.flush()
                await self._session.commit()
                logger.debug("session commit async")
                flush_graph_sync(
                    self._state,
                    self._graph_sync,
                    mode=self._graph_sync_mode,
                    mapper_for=self._mapper_for,
                )
            else:
                self._state.clear_graph_sync()
                await self._session.rollback()
                logger.debug("session rollback async exc_type=%s", exc_type.__name__)
        finally:
            await self._session.close()
            self._session = None
            logger.debug("session close async")

    async def rollback(self, *, clear_uow: bool = False) -> None:
        """Roll back the current SQLAlchemy transaction.

        Does not clear the unit-of-work queue unless ``clear_uow=True``.
        See ``docs/internals/session-lifecycle.md``.
        """
        await self._require_session().rollback()
        if clear_uow:
            self._state.clear_pending()
            self._state.clear_graph_sync()
        logger.debug("session rollback async explicit clear_uow=%s", clear_uow)

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
        identity: Any | None = None,
        iri: str | None = None,
    ) -> OntoModel | None:
        resolved_id = validate_get_identity(identity=identity, iri=iri)
        if resolved_id is not None:
            cached = self._state.get_cached(entity_type, resolved_id)
            if cached is not None:
                return cached
        mapper_cls = self._mapper_for(entity_type)
        plan = compile_select_plan(
            mapper_cls,
            id_value=resolved_id,
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
        return await async_reload_after_save(
            instance,
            mapper_cls,
            plan,
            inserted_id,
            get_fn=self.get,
        )

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
        return await async_load_snapshot_from_db(
            instance,
            mapper_cls,
            run_select=lambda stmt: self._require_session().execute(stmt),
        )

    async def save(self, instance: OntoModel, *, flush_now: bool = True) -> OntoModel:
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
        if flush_now:
            inserted_id = await self._execute_write(plan)
            return await self._queue_graph_sync_after_save(instance, mapper_cls, plan, inserted_id)
        self._state.pending.append(plan)
        return instance

    async def delete(self, instance: OntoModel, *, flush_now: bool = True) -> None:
        mapper_cls = self._mapper_for(type(instance))
        plan = compile_delete_plan(mapper_cls, instance)
        if flush_now:
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
        """Apply all pending save/delete plans (stops on first error; queue preserved)."""
        while self._state.pending:
            item = self._state.pending[0]
            if isinstance(item, WritePlan):
                plan = item
                inserted_id = await self._execute_write(plan)
                entity_type = plan.mapper_cls.entity
                identity = identity_from_write_plan(plan, inserted_id)
                if identity is not None and self._graph_sync is not None:
                    reloaded = await self.get(entity_type, identity=identity)
                    if reloaded is not None:
                        queue_graph_push(self._state, reloaded)
            elif isinstance(item, PendingDelete):
                await self._apply_pending_delete(item)
            self._state.pending.pop(0)
        logger.debug("session flush async complete")

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
