"""Shared flush coordinator for sync and async sessions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ontosql._log import logger
from ontosql.compile.plan import WritePlan
from ontosql.session._ops import identity_from_write_plan, merge_identity_into_instance
from ontosql.session.graph_sync import queue_graph_push
from ontosql.session.pending_queue import PendingDelete
from ontosql.session.state import SessionState


def flush_pending(
    state: SessionState,
    *,
    execute_write: Callable[[WritePlan], Any],
    apply_pending_delete: Callable[[PendingDelete], None],
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
) -> None:
    """Apply pending save/delete plans; stops on first error (unprocessed queue preserved)."""
    if not state.pending:
        return
    queue = list(state.pending)
    processed = 0
    pushes_before = len(state.graph_sync_pushes)
    removes_before = len(state.graph_sync_removes)
    try:
        for item in queue:
            if isinstance(item, WritePlan):
                plan = item
                source_instance = state.peek_pending_instance(plan)
                prior_nested = state.prior_nested_for_plan(plan) or frozenset()
                inserted_id = execute_write(plan)
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
            elif isinstance(item, PendingDelete):
                apply_pending_delete(item)
            processed += 1
    except Exception:
        state.pending = queue[processed:]
        state.restore_graph_sync(
            pushes_from=pushes_before,
            removes_from=removes_before,
        )
        raise
    state.pending_queue.clear_after_flush()
    logger.debug("session flush complete")


async def flush_pending_async(
    state: SessionState,
    *,
    execute_write: Callable[[WritePlan], Any],
    apply_pending_delete: Callable[[PendingDelete], Any],
    reload_for_graph: Callable[[type[Any], Any], Any],
    graph_sync_enabled: bool,
) -> None:
    """Async variant of flush_pending."""
    if not state.pending:
        return
    queue = list(state.pending)
    processed = 0
    pushes_before = len(state.graph_sync_pushes)
    removes_before = len(state.graph_sync_removes)
    try:
        for item in queue:
            if isinstance(item, WritePlan):
                plan = item
                source_instance = state.peek_pending_instance(plan)
                prior_nested = state.prior_nested_for_plan(plan) or frozenset()
                inserted_id = await execute_write(plan)
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
            elif isinstance(item, PendingDelete):
                await apply_pending_delete(item)
            processed += 1
    except Exception:
        state.pending = queue[processed:]
        state.restore_graph_sync(
            pushes_from=pushes_before,
            removes_from=removes_before,
        )
        raise
    state.pending_queue.clear_after_flush()
    logger.debug("session flush async complete")
