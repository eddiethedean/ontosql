"""Asynchronous AsyncOntoSession."""

from __future__ import annotations

import warnings
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel

from ontosql._log import logger
from ontosql.compile.execute import async_execute_delete_plan, async_execute_write_plan
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.select import compile_count_statement, compile_select_plan
from ontosql.compile.write import compile_delete_plan, count_scalar
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session._flush import flush_pending_async
from ontosql.session._ops import (
    _merge_snapshots_for_save,
    compile_save_plan_for_instance,
    identity_from_write_plan,
    resolve_save_is_new_and_snapshot,
    validate_get_identity,
)
from ontosql.session._sql import async_load_snapshot_from_db, async_reload_after_save
from ontosql.session.base import GraphSyncTargetLike, SessionBase
from ontosql.session.collections import attach_collections_async
from ontosql.session.graph_sync import (
    flush_graph_sync,
    prior_nested_iris_for_save,
    queue_graph_push,
    queue_graph_remove,
)
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
        registry: PrefixRegistry | None = None,
        strict_updates: bool = True,
    ) -> None:
        super().__init__(maps)
        self._engine = engine
        self._maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self._session: AsyncSession | None = None
        self._closed = False
        self._graph_sync = graph_sync
        self._graph_sync_mode = graph_sync_mode
        self._registry_prefix = registry
        self._strict_updates = strict_updates

    async def __aenter__(self) -> AsyncOntoSession:
        self._session = self._maker()
        self._closed = False
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
                    registry=self._registry_prefix,
                )
            else:
                self._state.clear_pending()
                self._state.clear_graph_sync()
                await self._session.rollback()
                logger.debug("session rollback async exc_type=%s", exc_type.__name__)
        finally:
            await self._session.close()
            self._session = None
            self._closed = True
            logger.debug("session close async")

    def __del__(self) -> None:
        if self._session is not None and not self._closed:
            warnings.warn(
                "AsyncOntoSession was not closed; "
                "use 'async with AsyncOntoSession(...) as session:'",
                ResourceWarning,
                stacklevel=2,
            )

    async def rollback(self, *, clear_uow: bool = True) -> None:
        """Roll back the current SQLAlchemy transaction.

        Clears the unit-of-work queue by default (``clear_uow=True``).
        See ``docs/internals/session-lifecycle.md``.
        """
        await self._require_session().rollback()
        self._state.clear_graph_sync()
        if clear_uow:
            self._state.clear_pending()
        elif self._state.pending:
            warnings.warn(
                "rollback(clear_uow=False) left pending save/delete queues; "
                "they may flush on session exit",
                stacklevel=2,
            )
        logger.debug("session rollback async explicit clear_uow=%s", clear_uow)

    def create_tables(self, *models: type[SQLModel]) -> None:
        """Create physical tables (convenience for tests)."""
        SQLModel.metadata.create_all(self._engine, tables=[m.__table__ for m in models])  # type: ignore[attr-defined]

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
            if self._state.is_pending_delete(entity_type, resolved_id):
                return None
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
        if iri is not None:
            loaded_id = getattr(instance, mapper_cls.identity_field, None)
            if loaded_id is not None and self._state.is_pending_delete(entity_type, loaded_id):
                return None
            if loaded_id is not None:
                cached = self._state.get_cached(entity_type, loaded_id)
                if cached is not None:
                    return cached
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
        result_list: list[OntoModel] = []
        for inst in instances:
            identity = getattr(inst, mapper_cls.identity_field, None)
            if identity is not None and self._state.is_pending_delete(entity_type, identity):
                continue
            result_list.append(self._register(inst))
        return result_list

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
        total = count_scalar(row)
        return max(0, total - self._state.count_pending_deletes(entity_type))

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
        *,
        prior_nested_iris: frozenset[str],
    ) -> OntoModel:
        reloaded = await self._reload_after_save(instance, mapper_cls, plan, inserted_id)
        if self._graph_sync is not None:
            queue_graph_push(self._state, reloaded, prior_nested_iris=prior_nested_iris)
        return reloaded

    async def _load_snapshot_from_db(
        self, instance: OntoModel, mapper_cls: type[Any]
    ) -> dict[str, Any] | None:
        return await async_load_snapshot_from_db(
            instance,
            mapper_cls,
            run_select=lambda stmt: self._require_session().execute(stmt),
        )

    async def _remove_snapshot_for_delete(
        self, instance: OntoModel, mapper_cls: type[Any]
    ) -> dict[str, Any] | None:
        db_snapshot = await self._load_snapshot_from_db(instance, mapper_cls)
        session_snapshot = self._state.get_snapshot(instance)
        return _merge_snapshots_for_save(session_snapshot, db_snapshot)

    def _queue_graph_remove_for_delete(
        self, instance: OntoModel, mapper_cls: type[Any], snapshot: dict[str, Any] | None
    ) -> None:
        if self._graph_sync is None:
            return
        queue_graph_remove(self._state, instance, snapshot=snapshot)

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
        prior_nested = prior_nested_iris_for_save(
            self._state,
            instance,
            mapper_cls,
            snapshot,
            self._registry_prefix,
        )
        if flush_now:
            inserted_id = await self._execute_write(plan)
            return await self._queue_graph_sync_after_save(
                instance,
                mapper_cls,
                plan,
                inserted_id,
                prior_nested_iris=prior_nested,
            )
        self._state.queue_pending_write(plan, instance, prior_nested_iris=prior_nested)
        return instance

    async def delete(self, instance: OntoModel, *, flush_now: bool = True) -> None:
        mapper_cls = self._mapper_for(type(instance))
        snapshot = await self._remove_snapshot_for_delete(instance, mapper_cls)
        plan = compile_delete_plan(mapper_cls, instance, snapshot=snapshot)
        identity = getattr(instance, mapper_cls.identity_field, None)
        if flush_now:
            await self._execute_delete(plan)
            self._queue_graph_remove_for_delete(instance, mapper_cls, snapshot)
        else:
            if identity is not None:
                self._state.mark_pending_delete(type(instance), identity)
            self._state.pending.append(
                PendingDelete(plan=plan, instance=instance, snapshot=snapshot)
            )

    async def _apply_pending_delete(self, pending: PendingDelete) -> None:
        await self._execute_delete(pending.plan)
        if self._graph_sync is not None:
            queue_graph_remove(
                self._state,
                pending.instance,
                snapshot=pending.snapshot,
            )

    async def flush(self) -> None:
        """Apply pending save/delete plans; stops on first error (unprocessed queue preserved)."""
        await flush_pending_async(
            self._state,
            execute_write=self._execute_write,
            apply_pending_delete=self._apply_pending_delete,
            reload_for_graph=lambda et, ident: self.get(et, identity=ident),
            graph_sync_enabled=self._graph_sync is not None,
        )

    async def _execute_write(self, plan: WritePlan) -> Any:
        session = self._require_session()
        returned = await async_execute_write_plan(
            session,
            plan,
            mapper_registry=self._registry,
            strict_updates=self._strict_updates,
        )
        identity = identity_from_write_plan(plan, returned)
        if identity is not None:
            self._state.expire(plan.mapper_cls.entity, identity)
        return identity

    async def _execute_delete(self, plan: DeletePlan) -> None:
        await async_execute_delete_plan(
            self._require_session(),
            plan,
            mapper_registry=self._registry,
        )
        if plan.root.where:
            identity = next(iter(plan.root.where.values()))
            self._state.expire(plan.mapper_cls.entity, identity)
