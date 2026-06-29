"""Session identity map, snapshots, and pending write queue (facade)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontosql.compile.plan import WritePlan
from ontosql.semantic.model import OntoModel
from ontosql.session.graph_queue import GraphPushEntry, GraphRemoveEntry, GraphSyncQueue
from ontosql.session.identity_map import IdentityMap, SnapshotKey
from ontosql.session.pending_queue import PendingDelete, PendingWorkQueue

PendingDeleteKey = SnapshotKey

# Re-export for backward compatibility
__all__ = [
    "GraphPushEntry",
    "GraphRemoveEntry",
    "PendingDelete",
    "PendingDeleteKey",
    "SessionState",
    "SnapshotKey",
]


@dataclass
class SessionState:
    """Unit-of-work state for OntoSession."""

    identity: IdentityMap = field(default_factory=IdentityMap)
    pending_queue: PendingWorkQueue = field(default_factory=PendingWorkQueue)
    graph_queue: GraphSyncQueue = field(default_factory=GraphSyncQueue)

    # --- Identity map delegation ---
    @property
    def identity_map(self) -> dict[tuple[type[OntoModel], Any], OntoModel]:
        return self.identity.identity_map

    @property
    def snapshots(self) -> dict[SnapshotKey, dict[str, Any]]:
        return self.identity.snapshots

    @property
    def pending_deletes(self) -> set[PendingDeleteKey]:
        return self.identity.pending_deletes

    def snapshot_key(self, instance: OntoModel) -> SnapshotKey | None:
        return self.identity.snapshot_key(instance)

    def get_snapshot(self, instance: OntoModel) -> dict[str, Any] | None:
        return self.identity.get_snapshot(instance)

    def register(self, instance: OntoModel) -> None:
        self.identity.register(instance)

    def get_cached(self, entity_type: type[OntoModel], identity: Any) -> OntoModel | None:
        return self.identity.get_cached(entity_type, identity)

    def is_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> bool:
        return self.identity.is_pending_delete(entity_type, identity)

    def mark_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> None:
        self.identity.mark_pending_delete(entity_type, identity)

    def clear_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> None:
        self.identity.clear_pending_delete(entity_type, identity)

    def clear_all_pending_delete_tombstones(self) -> None:
        self.identity.clear_all_pending_delete_tombstones()

    def expire(self, entity_type: type[OntoModel], identity: Any) -> None:
        self.identity.expire(entity_type, identity)

    def expire_all(self) -> None:
        self.identity.expire_all()

    def count_pending_deletes(self, entity_type: type[OntoModel]) -> int:
        return self.identity.count_pending_deletes(entity_type)

    # --- Pending queue delegation ---
    @property
    def pending(self) -> list[WritePlan | PendingDelete]:
        return self.pending_queue.pending

    @pending.setter
    def pending(self, value: list[WritePlan | PendingDelete]) -> None:
        self.pending_queue.pending = value

    @property
    def pending_instances(self) -> dict[int, OntoModel]:
        return self.pending_queue.pending_instances

    @property
    def pending_insert_objects(self) -> set[int]:
        return self.pending_queue.pending_insert_objects

    @property
    def pending_prior_nested(self) -> dict[int, frozenset[str]]:
        return self.pending_queue.pending_prior_nested

    def queue_pending_write(
        self,
        plan: WritePlan,
        instance: OntoModel,
        *,
        prior_nested_iris: frozenset[str] | None = None,
    ) -> None:
        self.pending_queue.queue_pending_write(plan, instance, prior_nested_iris=prior_nested_iris)

    def prior_nested_for_plan(self, plan: WritePlan) -> frozenset[str] | None:
        return self.pending_queue.prior_nested_for_plan(plan)

    def peek_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        return self.pending_queue.peek_pending_instance(plan)

    def pop_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        return self.pending_queue.pop_pending_instance(plan)

    def clear_pending(self) -> None:
        self.pending_queue.clear()
        self.identity.pending_deletes.clear()

    # --- Graph queue delegation ---
    @property
    def graph_sync_pushes(self) -> list[GraphPushEntry]:
        return self.graph_queue.graph_sync_pushes

    @property
    def graph_sync_removes(self) -> list[GraphRemoveEntry]:
        return self.graph_queue.graph_sync_removes

    @property
    def graph_sync_failures(self) -> list[Any]:
        return self.graph_queue.graph_sync_failures

    def restore_graph_sync(self, *, pushes_from: int, removes_from: int) -> None:
        self.graph_queue.restore(pushes_from=pushes_from, removes_from=removes_from)

    def clear_graph_sync(self) -> None:
        self.graph_queue.clear()

    @property
    def has_graph_sync_pending(self) -> bool:
        return self.graph_queue.has_pending
