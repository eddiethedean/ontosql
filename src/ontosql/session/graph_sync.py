"""Deferred graph sync helpers for OntoSession."""

from __future__ import annotations

from typing import Any

from ontosql.semantic.model import OntoModel
from ontosql.session.state import SessionState
from ontosql.sync.graph import GraphSyncMode


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
    """Apply queued graph sync operations (call only after successful SQL commit)."""
    if graph_sync is None:
        return
    from ontosql.sync import push_instance, remove_instance

    for instance in state.graph_sync_removes:
        remove_instance(
            instance,
            graph_sync,
            mapper_cls=mapper_for(type(instance)),
        )
    for instance in state.graph_sync_pushes:
        push_instance(
            instance,
            graph_sync,
            mode=mode,
            mapper_cls=mapper_for(type(instance)),
        )
    state.clear_graph_sync()
