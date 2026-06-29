"""Shared flush coordinator for sync and async sessions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ontosql._log import logger
from ontosql.compile.plan import WritePlan
from ontosql.session._ops import identity_from_write_plan, merge_identity_into_instance
from ontosql.session.graph_sync import queue_graph_push
from ontosql.session.pending_queue import PendingDelete, PendingWorkQueue
from ontosql.session.state import SessionState


def _process_write_plan(
    state: SessionState,
    plan: WritePlan,
    *,
    execute_write: Callable[[WritePlan], Any],
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
    queue: PendingWorkQueue,
) -> None:
    source_instance = state.peek_pending_instance(plan)
    prior_nested = state.prior_nested_for_plan(plan) or frozenset()
    cached_sql = queue.sql_result_for_plan(plan)
    if cached_sql is not None:
        inserted_id = cached_sql
    else:
        inserted_id = execute_write(plan)
        queue.mark_sql_applied(plan, inserted_id)
    state.pop_pending_instance(plan)
    state.pending_prior_nested.pop(id(plan), None)
    if source_instance is not None:
        merge_identity_into_instance(
            source_instance,
            plan.mapper_cls,
            identity_from_write_plan(plan, inserted_id),
        )
    entity_type = plan.mapper_cls.entity
    identity = identity_from_write_plan(plan, inserted_id)
    if identity is not None and graph_sync_enabled:
        reloaded = reload_for_graph(entity_type, identity)
        if reloaded is not None:
            queue_graph_push(state, reloaded, prior_nested_iris=prior_nested)
    queue.clear_sql_applied(plan)


def _process_pending_delete(
    pending: PendingDelete,
    *,
    state: SessionState,
    pending_delete_sql: Callable[[PendingDelete], None],
    queue_pending_delete_graph: Callable[[PendingDelete], None] | None,
    queue: PendingWorkQueue,
) -> None:
    if not queue.is_delete_sql_applied(pending):
        pending_delete_sql(pending)
        queue.mark_delete_sql_applied(pending)
    if queue_pending_delete_graph is not None:
        queue_pending_delete_graph(pending)
    queue.clear_delete_sql_applied(pending)


def flush_pending(
    state: SessionState,
    *,
    execute_write: Callable[[WritePlan], Any],
    pending_delete_sql: Callable[[PendingDelete], None],
    queue_pending_delete_graph: Callable[[PendingDelete], None] | None,
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
) -> None:
    """Apply pending save/delete plans; stops on first error (unprocessed queue preserved)."""
    if not state.pending:
        return
    queue = state.pending_queue
    items = list(state.pending)
    done = 0
    try:
        for item in items:
            iter_pushes = len(state.graph_sync_pushes)
            iter_removes = len(state.graph_sync_removes)
            try:
                if isinstance(item, WritePlan):
                    _process_write_plan(
                        state,
                        item,
                        execute_write=execute_write,
                        reload_for_graph=reload_for_graph,
                        graph_sync_enabled=graph_sync_enabled,
                        queue=queue,
                    )
                elif isinstance(item, PendingDelete):
                    _process_pending_delete(
                        pending=item,
                        state=state,
                        pending_delete_sql=pending_delete_sql,
                        queue_pending_delete_graph=queue_pending_delete_graph,
                        queue=queue,
                    )
                done += 1
            except Exception:
                state.restore_graph_sync(
                    pushes_from=iter_pushes,
                    removes_from=iter_removes,
                )
                raise
    except Exception:
        state.pending = items[done:]
        raise
    queue.clear_after_flush()
    logger.debug("session flush complete")


async def _process_write_plan_async(
    state: SessionState,
    plan: WritePlan,
    *,
    execute_write: Callable[[WritePlan], Any],
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
    queue: PendingWorkQueue,
) -> None:
    source_instance = state.peek_pending_instance(plan)
    prior_nested = state.prior_nested_for_plan(plan) or frozenset()
    cached_sql = queue.sql_result_for_plan(plan)
    if cached_sql is not None:
        inserted_id = cached_sql
    else:
        inserted_id = await execute_write(plan)
        queue.mark_sql_applied(plan, inserted_id)
    state.pop_pending_instance(plan)
    state.pending_prior_nested.pop(id(plan), None)
    if source_instance is not None:
        merge_identity_into_instance(
            source_instance,
            plan.mapper_cls,
            identity_from_write_plan(plan, inserted_id),
        )
    entity_type = plan.mapper_cls.entity
    identity = identity_from_write_plan(plan, inserted_id)
    if identity is not None and graph_sync_enabled:
        reloaded = await reload_for_graph(entity_type, identity)
        if reloaded is not None:
            queue_graph_push(state, reloaded, prior_nested_iris=prior_nested)
    queue.clear_sql_applied(plan)


async def _process_pending_delete_async(
    pending: PendingDelete,
    *,
    state: SessionState,
    pending_delete_sql: Callable[[PendingDelete], Any],
    queue_pending_delete_graph: Callable[[PendingDelete], Any] | None,
    queue: PendingWorkQueue,
) -> None:
    if not queue.is_delete_sql_applied(pending):
        await pending_delete_sql(pending)
        queue.mark_delete_sql_applied(pending)
    if queue_pending_delete_graph is not None:
        await queue_pending_delete_graph(pending)
    queue.clear_delete_sql_applied(pending)


async def flush_pending_async(
    state: SessionState,
    *,
    execute_write: Callable[[WritePlan], Any],
    pending_delete_sql: Callable[[PendingDelete], Any],
    queue_pending_delete_graph: Callable[[PendingDelete], Any] | None,
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
) -> None:
    """Async variant of flush_pending."""
    if not state.pending:
        return
    queue = state.pending_queue
    items = list(state.pending)
    done = 0
    try:
        for item in items:
            iter_pushes = len(state.graph_sync_pushes)
            iter_removes = len(state.graph_sync_removes)
            try:
                if isinstance(item, WritePlan):
                    await _process_write_plan_async(
                        state,
                        item,
                        execute_write=execute_write,
                        reload_for_graph=reload_for_graph,
                        graph_sync_enabled=graph_sync_enabled,
                        queue=queue,
                    )
                elif isinstance(item, PendingDelete):
                    await _process_pending_delete_async(
                        pending=item,
                        state=state,
                        pending_delete_sql=pending_delete_sql,
                        queue_pending_delete_graph=queue_pending_delete_graph,
                        queue=queue,
                    )
                done += 1
            except Exception:
                state.restore_graph_sync(
                    pushes_from=iter_pushes,
                    removes_from=iter_removes,
                )
                raise
    except Exception:
        state.pending = items[done:]
        raise
    queue.clear_after_flush()
    logger.debug("session flush async complete")
