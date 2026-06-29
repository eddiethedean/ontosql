"""Session identity map, snapshots, and pending write queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.semantic.model import OntoModel

SnapshotKey = tuple[type[OntoModel], Any]
PendingDeleteKey = tuple[type[OntoModel], Any]


@dataclass
class PendingDelete:
    """Queued delete plan with instance retained for deferred graph sync."""

    plan: DeletePlan
    instance: OntoModel
    snapshot: dict[str, Any] | None = None


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
class SessionState:
    """Unit-of-work state for OntoSession."""

    identity_map: dict[tuple[type[OntoModel], Any], OntoModel] = field(default_factory=dict)
    snapshots: dict[SnapshotKey, dict[str, Any]] = field(default_factory=dict)
    pending: list[WritePlan | PendingDelete] = field(default_factory=list)
    pending_instances: dict[int, OntoModel] = field(default_factory=dict)
    pending_deletes: set[PendingDeleteKey] = field(default_factory=set)
    pending_insert_objects: set[int] = field(default_factory=set)
    pending_prior_nested: dict[int, frozenset[str]] = field(default_factory=dict)
    graph_sync_pushes: list[GraphPushEntry] = field(default_factory=list)
    graph_sync_removes: list[GraphRemoveEntry] = field(default_factory=list)
    graph_sync_failures: list[Any] = field(default_factory=list)

    def snapshot_key(self, instance: OntoModel) -> SnapshotKey | None:
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if identity is None:
            return None
        return (entity_type, identity)

    def get_snapshot(self, instance: OntoModel) -> dict[str, Any] | None:
        key = self.snapshot_key(instance)
        if key is None:
            return None
        return self.snapshots.get(key)

    def register(self, instance: OntoModel) -> None:
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if identity is None:
            return
        key = (entity_type, identity)
        if key in self.identity_map and self.identity_map[key] is not instance:
            import warnings

            warnings.warn(
                f"Identity map entry for {entity_type.__name__}({identity!r}) replaced",
                stacklevel=3,
            )
        self.identity_map[key] = instance
        self.snapshots[key] = instance.model_dump()

    def get_cached(self, entity_type: type[OntoModel], identity: Any) -> OntoModel | None:
        key = (entity_type, identity)
        if key in self.pending_deletes:
            return None
        return self.identity_map.get(key)

    def is_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> bool:
        return (entity_type, identity) in self.pending_deletes

    def mark_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> None:
        self.pending_deletes.add((entity_type, identity))

    def clear_pending_delete(self, entity_type: type[OntoModel], identity: Any) -> None:
        self.pending_deletes.discard((entity_type, identity))

    def expire(self, entity_type: type[OntoModel], identity: Any) -> None:
        key = (entity_type, identity)
        self.identity_map.pop(key, None)
        self.snapshots.pop(key, None)
        self.clear_pending_delete(entity_type, identity)

    def queue_pending_write(
        self,
        plan: WritePlan,
        instance: OntoModel,
        *,
        prior_nested_iris: frozenset[str] | None = None,
    ) -> None:
        """Queue a deferred save; replaces an existing queued save for the same object."""
        obj_id = id(instance)
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if obj_id in self.pending_insert_objects:
            for idx, item in enumerate(self.pending):
                if isinstance(item, WritePlan) and self.pending_instances.get(id(item)) is instance:
                    old_plan_id = id(item)
                    self.pending[idx] = plan
                    self.pending_instances.pop(old_plan_id, None)
                    self.pending_instances[id(plan)] = instance
                    self.pending_prior_nested.pop(old_plan_id, None)
                    if prior_nested_iris is not None:
                        self.pending_prior_nested[id(plan)] = prior_nested_iris
                    return
        if identity is not None:
            for idx, item in enumerate(self.pending):
                if not isinstance(item, WritePlan):
                    continue
                other = self.pending_instances.get(id(item))
                if other is None:
                    continue
                other_id = getattr(other, other.identity_field, None)
                if other_id == identity and type(other) is entity_type:
                    old_plan_id = id(item)
                    self.pending[idx] = plan
                    self.pending_instances.pop(old_plan_id, None)
                    self.pending_instances[id(plan)] = instance
                    self.pending_prior_nested.pop(old_plan_id, None)
                    self.pending_insert_objects.discard(id(other))
                    self.pending_insert_objects.add(obj_id)
                    if prior_nested_iris is not None:
                        self.pending_prior_nested[id(plan)] = prior_nested_iris
                    return
        self.pending_insert_objects.add(obj_id)
        self.pending.append(plan)
        self.pending_instances[id(plan)] = instance
        if prior_nested_iris is not None:
            self.pending_prior_nested[id(plan)] = prior_nested_iris

    def prior_nested_for_plan(self, plan: WritePlan) -> frozenset[str] | None:
        return self.pending_prior_nested.get(id(plan))

    def peek_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        return self.pending_instances.get(id(plan))

    def pop_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        instance = self.pending_instances.pop(id(plan), None)
        if instance is not None:
            self.pending_insert_objects.discard(id(instance))
        return instance

    def clear_pending(self) -> None:
        self.pending.clear()
        self.pending_instances.clear()
        self.pending_deletes.clear()
        self.pending_insert_objects.clear()
        self.pending_prior_nested.clear()

    def count_pending_deletes(self, entity_type: type[OntoModel]) -> int:
        return sum(1 for et, _ in self.pending_deletes if et is entity_type)

    def restore_graph_sync(self, *, pushes_from: int, removes_from: int) -> None:
        """Truncate graph sync queues to lengths before a flush attempt."""
        if pushes_from < len(self.graph_sync_pushes):
            del self.graph_sync_pushes[pushes_from:]
        if removes_from < len(self.graph_sync_removes):
            del self.graph_sync_removes[removes_from:]

    def expire_all(self) -> None:
        """Evict all instances from the identity map and snapshots."""
        self.identity_map.clear()
        self.snapshots.clear()
        self.pending_deletes.clear()

    def clear_graph_sync(self) -> None:
        self.graph_sync_pushes.clear()
        self.graph_sync_removes.clear()
        self.graph_sync_failures.clear()

    @property
    def has_graph_sync_pending(self) -> bool:
        return bool(self.graph_sync_pushes or self.graph_sync_removes)
