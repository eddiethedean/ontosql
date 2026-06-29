"""Deferred graph sync helpers for OntoSession."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ontosql._log import logger
from ontosql.semantic.model import OntoModel
from ontosql.session.state import SessionState
from ontosql.sync.graph import GraphSyncMode

GraphSyncOperation = Literal["remove", "push"]


@dataclass
class GraphSyncFailure:
    """A single graph sync operation that failed after SQL commit."""

    instance: OntoModel
    operation: GraphSyncOperation
    error: Exception


class GraphSyncError(Exception):
    """Raised when graph sync fails after SQL commit (split-brain risk)."""

    def __init__(
        self,
        message: str,
        *,
        failure: GraphSyncFailure,
        pending_removes: int,
        pending_pushes: int,
    ) -> None:
        super().__init__(message)
        self.failure = failure
        self.pending_removes = pending_removes
        self.pending_pushes = pending_pushes


def queue_graph_push(state: SessionState, instance: OntoModel) -> None:
    """Queue an instance for graph push after SQL commit."""
    state.graph_sync_pushes.append(instance)


def queue_graph_remove(state: SessionState, instance: OntoModel) -> None:
    """Queue an instance for graph removal after SQL commit."""
    state.graph_sync_removes.append(instance)


def flush_graph_sync(
    state: SessionState,
    graph_sync: Any,
    *,
    mode: GraphSyncMode,
    mapper_for: Any,
) -> None:
    """Apply queued graph sync operations (call only after successful SQL commit).

    Processes removes then pushes one at a time. On failure, completed operations
    stay applied; remaining queue entries are preserved for ``retry_graph_sync()``.
    """
    if graph_sync is None:
        return
    from ontosql.sync import push_instance, remove_instance

    state.graph_sync_failures.clear()

    while state.graph_sync_removes:
        instance = state.graph_sync_removes[0]
        try:
            remove_instance(
                instance,
                graph_sync,
                mapper_cls=mapper_for(type(instance)),
            )
        except Exception as exc:
            failure = GraphSyncFailure(instance=instance, operation="remove", error=exc)
            state.graph_sync_failures.append(failure)
            logger.warning(
                "graph sync remove failed after SQL commit entity=%s op=remove",
                type(instance).__name__,
                exc_info=exc,
            )
            raise GraphSyncError(
                f"Graph sync remove failed for {type(instance).__name__}; "
                f"{len(state.graph_sync_removes)} remove(s) and "
                f"{len(state.graph_sync_pushes)} push(es) still queued. "
                "SQL is already committed — call retry_graph_sync() after fixing the graph target.",
                failure=failure,
                pending_removes=len(state.graph_sync_removes),
                pending_pushes=len(state.graph_sync_pushes),
            ) from exc
        state.graph_sync_removes.pop(0)
        logger.debug("graph sync remove ok entity=%s", type(instance).__name__)

    while state.graph_sync_pushes:
        instance = state.graph_sync_pushes[0]
        try:
            push_instance(
                instance,
                graph_sync,
                mode=mode,
                mapper_cls=mapper_for(type(instance)),
            )
        except Exception as exc:
            failure = GraphSyncFailure(instance=instance, operation="push", error=exc)
            state.graph_sync_failures.append(failure)
            logger.warning(
                "graph sync push failed after SQL commit entity=%s op=push",
                type(instance).__name__,
                exc_info=exc,
            )
            raise GraphSyncError(
                f"Graph sync push failed for {type(instance).__name__}; "
                f"{len(state.graph_sync_pushes)} push(es) still queued. "
                "SQL is already committed — call retry_graph_sync() after fixing the graph target.",
                failure=failure,
                pending_removes=0,
                pending_pushes=len(state.graph_sync_pushes),
            ) from exc
        state.graph_sync_pushes.pop(0)
        logger.debug("graph sync push ok entity=%s", type(instance).__name__)
