"""Identity map and change snapshots."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

from ontosql.semantic.model import OntoModel

SnapshotKey = tuple[type[OntoModel], Any]


@dataclass
class IdentityMap:
    """Caches loaded instances and their snapshots."""

    identity_map: dict[SnapshotKey, OntoModel] = field(default_factory=dict)
    snapshots: dict[SnapshotKey, dict] = field(default_factory=dict)
    pending_deletes: set[SnapshotKey] = field(default_factory=set)

    def snapshot_key(self, instance: OntoModel) -> SnapshotKey | None:
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if identity is None:
            return None
        return (entity_type, identity)

    def get_snapshot(self, instance: OntoModel) -> dict | None:
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
            warnings.warn(
                f"Identity map entry for {entity_type.__name__}({identity!r}) replaced",
                stacklevel=3,
            )
        self.identity_map[key] = instance
        self.snapshots[key] = instance.model_dump()

    def get_cached(self, entity_type: type[OntoModel], identity: object) -> OntoModel | None:
        key = (entity_type, identity)
        if key in self.pending_deletes:
            return None
        return self.identity_map.get(key)

    def is_pending_delete(self, entity_type: type[OntoModel], identity: object) -> bool:
        return (entity_type, identity) in self.pending_deletes

    def mark_pending_delete(self, entity_type: type[OntoModel], identity: object) -> None:
        self.pending_deletes.add((entity_type, identity))

    def clear_pending_delete(self, entity_type: type[OntoModel], identity: object) -> None:
        self.pending_deletes.discard((entity_type, identity))

    def clear_all_pending_delete_tombstones(self) -> None:
        """Clear pending-delete markers without touching the pending write queue."""
        self.pending_deletes.clear()

    def expire(self, entity_type: type[OntoModel], identity: object) -> None:
        key = (entity_type, identity)
        self.identity_map.pop(key, None)
        self.snapshots.pop(key, None)
        self.clear_pending_delete(entity_type, identity)

    def expire_all(self) -> None:
        self.identity_map.clear()
        self.snapshots.clear()
        self.pending_deletes.clear()

    def count_pending_deletes(self, entity_type: type[OntoModel]) -> int:
        return sum(1 for et, _ in self.pending_deletes if et is entity_type)
