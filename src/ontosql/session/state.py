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


@dataclass
class SessionState:
    """Unit-of-work state for OntoSession."""

    identity_map: dict[tuple[type[OntoModel], Any], OntoModel] = field(default_factory=dict)
    snapshots: dict[SnapshotKey, dict[str, Any]] = field(default_factory=dict)
    pending: list[WritePlan | PendingDelete] = field(default_factory=list)
    pending_instances: dict[int, OntoModel] = field(default_factory=dict)
    pending_deletes: set[PendingDeleteKey] = field(default_factory=set)
    pending_insert_objects: set[int] = field(default_factory=set)
    graph_sync_pushes: list[OntoModel] = field(default_factory=list)
    graph_sync_removes: list[OntoModel] = field(default_factory=list)
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

    def queue_pending_write(self, plan: WritePlan, instance: OntoModel) -> None:
        """Queue a deferred save; replaces an existing queued save for the same object."""
        obj_id = id(instance)
        if obj_id in self.pending_insert_objects:
            for idx, item in enumerate(self.pending):
                if isinstance(item, WritePlan) and self.pending_instances.get(id(item)) is instance:
                    self.pending[idx] = plan
                    self.pending_instances.pop(id(item), None)
                    self.pending_instances[id(plan)] = instance
                    return
        self.pending_insert_objects.add(obj_id)
        self.pending.append(plan)
        self.pending_instances[id(plan)] = instance

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

    def clear_graph_sync(self) -> None:
        self.graph_sync_pushes.clear()
        self.graph_sync_removes.clear()
        self.graph_sync_failures.clear()

    @property
    def has_graph_sync_pending(self) -> bool:
        return bool(self.graph_sync_pushes or self.graph_sync_removes)
