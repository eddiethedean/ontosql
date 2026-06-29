"""Post-commit graph sync queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontosql.semantic.model import OntoModel


@dataclass
class GraphPushEntry:
    """Queued graph push with pre-save nested IRIs for stale retraction."""

    instance: OntoModel
    prior_nested_iris: frozenset[str] = field(default_factory=frozenset)


@dataclass
class GraphRemoveEntry:
    """Queued graph remove with optional DB/session snapshot for nested IRIs."""

    instance: OntoModel
    snapshot: dict[str, Any] | None = None


@dataclass
class GraphSyncQueue:
    """Queues graph sync operations after SQL commit."""

    graph_sync_pushes: list[GraphPushEntry] = field(default_factory=list)
    graph_sync_removes: list[GraphRemoveEntry] = field(default_factory=list)
    graph_sync_failures: list[Any] = field(default_factory=list)

    def restore(self, *, pushes_from: int, removes_from: int) -> None:
        if pushes_from < len(self.graph_sync_pushes):
            del self.graph_sync_pushes[pushes_from:]
        if removes_from < len(self.graph_sync_removes):
            del self.graph_sync_removes[removes_from:]

    def clear(self) -> None:
        self.graph_sync_pushes.clear()
        self.graph_sync_removes.clear()
        self.graph_sync_failures.clear()

    @property
    def has_pending(self) -> bool:
        return bool(self.graph_sync_pushes or self.graph_sync_removes)
