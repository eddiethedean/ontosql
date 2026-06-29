"""Synchronous OntoSession."""

from __future__ import annotations

import warnings
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from ontosql._log import logger
from ontosql.compile.execute import execute_delete_plan, execute_write_plan
from ontosql.compile.plan import WritePlan
from ontosql.compile.select import compile_count_statement, compile_select_plan
from ontosql.compile.write import compile_delete_plan, count_scalar
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session._ops import (
    compile_save_plan_for_instance,
    identity_from_write_plan,
    merge_identity_into_instance,
    resolve_save_is_new_and_snapshot,
    validate_get_identity,
)
from ontosql.session._sql import load_snapshot_from_db, reload_after_save
from ontosql.session.base import GraphSyncTargetLike, SessionBase
from ontosql.session.collections import attach_collections
from ontosql.session.graph_sync import (
    flush_graph_sync,
    prior_nested_iris_for_save,
    queue_graph_push,
    queue_graph_remove,
)
from ontosql.session.hydrate import hydrate_first, hydrate_row
from ontosql.session.state import PendingDelete
from ontosql.sync.graph import GraphSyncMode


class OntoSession(SessionBase):
    """Synchronous unit of work for semantic CRUD over SQL.

    Always use as a context manager::

        with OntoSession(engine, maps=[...]) as session:
            ...
    """

    def __init__(
        self,
        engine: Engine,
        maps: list[type[Any]] | None = None,
        *,
        graph_sync: GraphSyncTargetLike | None = None,
        graph_sync_mode: GraphSyncMode = "patch",
        registry: PrefixRegistry | None = None,
        strict_updates: bool = True,
    ) -> None:
        super().__init__(maps)
        self._engine = engine
        self._session: Session | None = None
        self._closed = False
        self._graph_sync = graph_sync
        self._graph_sync_mode = graph_sync_mode
        self._registry_prefix = registry
        self._strict_updates = strict_updates

    def __enter__(self) -> OntoSession:
        self._session = Session(self._engine)
        self._closed = False
        logger.debug("session open sync")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                if self._state.pending:
                    self.flush()
                self._session.commit()
                logger.debug("session commit sync")
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
                self._session.rollback()
                logger.debug("session rollback sync exc_type=%s", exc_type.__name__)
        finally:
            self._session.close()
            self._session = None
            self._closed = True
            logger.debug("session close sync")

    def __del__(self) -> None:
        if self._session is not None and not self._closed:
            warnings.warn(
                "OntoSession was not closed; use 'with OntoSession(...) as session:'",
                ResourceWarning,
                stacklevel=2,
            )

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError(
                "OntoSession is not active; use 'with OntoSession(engine, maps=[...]) as session:'"
            )
        return self._session

    def rollback(self, *, clear_uow: bool = True) -> None:
        """Roll back the current SQLAlchemy transaction.

        Clears the unit-of-work queue by default (``clear_uow=True``).
        See ``docs/internals/session-lifecycle.md``.
        """
        self._require_session().rollback()
        if clear_uow:
            self._state.clear_pending()
            self._state.clear_graph_sync()
        elif self._state.pending or self._state.has_graph_sync_pending:
            warnings.warn(
                "rollback(clear_uow=False) left pending save/delete or graph sync queues; "
                "they may flush on session exit",
                stacklevel=2,
            )
        logger.debug("session rollback sync explicit clear_uow=%s", clear_uow)

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
        instance = hydrate_first(plan, self._require_session().exec(plan.select))
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
        attach_collections(self._require_session(), mapper_cls, [instance])
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
        rows = self._require_session().exec(plan.select).all()
        instances = [hydrate_row(plan, row) for row in rows]
        attach_collections(self._require_session(), mapper_cls, instances)
        result: list[OntoModel] = []
        for inst in instances:
            identity = getattr(inst, mapper_cls.identity_field, None)
            if identity is not None and self._state.is_pending_delete(entity_type, identity):
                continue
            result.append(self._register(inst))
        return result

    def count(
        self,
        entity_type: type[OntoModel],
        *,
        where: Any | None = None,
    ) -> int:
        mapper_cls = self._mapper_for(entity_type)
        stmt = compile_count_statement(mapper_cls, where=where)
        result = self._require_session().exec(stmt).one()
        return count_scalar(result)

    def _reload_after_save(
        self,
        instance: OntoModel,
        mapper_cls: type[Any],
        plan: WritePlan,
        inserted_id: Any,
    ) -> OntoModel:
        return reload_after_save(
            instance,
            mapper_cls,
            plan,
            inserted_id,
            get_fn=self.get,
        )

    def _queue_graph_sync_after_save(
        self,
        instance: OntoModel,
        mapper_cls: type[Any],
        plan: WritePlan,
        inserted_id: Any,
        *,
        prior_nested_iris: frozenset[str],
    ) -> OntoModel:
        reloaded = self._reload_after_save(instance, mapper_cls, plan, inserted_id)
        if self._graph_sync is not None:
            queue_graph_push(self._state, reloaded, prior_nested_iris=prior_nested_iris)
        return reloaded

    def _load_snapshot_from_db(
        self, instance: OntoModel, mapper_cls: type[Any]
    ) -> dict[str, Any] | None:
        return load_snapshot_from_db(
            instance,
            mapper_cls,
            run_select=lambda stmt: self._require_session().exec(stmt),
        )

    def save(self, instance: OntoModel, *, flush_now: bool = True) -> OntoModel:
        mapper_cls = self._mapper_for(type(instance))
        is_new = self._is_new_instance(mapper_cls, instance)
        db_snapshot = self._load_snapshot_from_db(instance, mapper_cls)
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
            inserted_id = self._execute_write(plan)
            return self._queue_graph_sync_after_save(
                instance,
                mapper_cls,
                plan,
                inserted_id,
                prior_nested_iris=prior_nested,
            )
        self._state.queue_pending_write(plan, instance)
        return instance

    def delete(self, instance: OntoModel, *, flush_now: bool = True) -> None:
        mapper_cls = self._mapper_for(type(instance))
        plan = compile_delete_plan(mapper_cls, instance)
        identity = getattr(instance, mapper_cls.identity_field, None)
        if flush_now:
            execute_delete_plan(self._require_session(), plan)
            if identity is not None:
                self._state.expire(type(instance), identity)
            if self._graph_sync is not None:
                queue_graph_remove(self._state, instance)
        else:
            if identity is not None:
                self._state.mark_pending_delete(type(instance), identity)
            self._state.pending.append(PendingDelete(plan=plan, instance=instance))

    def _apply_pending_delete(self, pending: PendingDelete) -> None:
        execute_delete_plan(self._require_session(), pending.plan)
        mapper_cls = pending.plan.mapper_cls
        identity = getattr(pending.instance, mapper_cls.identity_field, None)
        if identity is not None:
            self._state.expire(mapper_cls.entity, identity)
        if self._graph_sync is not None:
            queue_graph_remove(self._state, pending.instance)

    def flush(self) -> None:
        """Apply pending save/delete plans; stops on first error (unprocessed queue preserved)."""
        if not self._state.pending:
            return
        queue = list(self._state.pending)
        processed = 0
        try:
            for item in queue:
                if isinstance(item, WritePlan):
                    plan = item
                    source_instance = self._state.peek_pending_instance(plan)
                    prior_nested = frozenset()
                    if self._graph_sync is not None and source_instance is not None:
                        prior_nested = prior_nested_iris_for_save(
                            self._state,
                            source_instance,
                            plan.mapper_cls,
                            self._state.get_snapshot(source_instance),
                            self._registry_prefix,
                        )
                    inserted_id = self._execute_write(plan)
                    self._state.pop_pending_instance(plan)
                    if source_instance is not None:
                        merge_identity_into_instance(
                            source_instance,
                            plan.mapper_cls,
                            identity_from_write_plan(plan, inserted_id),
                        )
                    entity_type = plan.mapper_cls.entity
                    identity = identity_from_write_plan(plan, inserted_id)
                    if identity is not None and self._graph_sync is not None:
                        reloaded = self.get(entity_type, identity=identity)
                        if reloaded is not None:
                            queue_graph_push(
                                self._state,
                                reloaded,
                                prior_nested_iris=prior_nested,
                            )
                elif isinstance(item, PendingDelete):
                    self._apply_pending_delete(item)
                processed += 1
        except Exception:
            self._state.pending = queue[processed:]
            raise
        self._state.pending.clear()
        self._state.pending_instances.clear()
        self._state.pending_insert_objects.clear()
        logger.debug("session flush sync complete")

    def _execute_write(self, plan: WritePlan) -> Any:
        returned = execute_write_plan(
            self._require_session(),
            plan,
            mapper_registry=self._registry,
            strict_updates=self._strict_updates,
        )
        identity = identity_from_write_plan(plan, returned)
        if identity is not None:
            self._state.expire(plan.mapper_cls.entity, identity)
        return identity
