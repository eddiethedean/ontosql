"""Session identity map, snapshots, and pending write queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.semantic.model import OntoModel


@dataclass
class SessionState:
    """Unit-of-work state for OntoSession."""

    identity_map: dict[tuple[type[OntoModel], Any], OntoModel] = field(default_factory=dict)
    snapshots: dict[int, dict[str, Any]] = field(default_factory=dict)
    pending: list[WritePlan | DeletePlan] = field(default_factory=list)

    def identity_key(
        self, entity_type: type[OntoModel], instance: OntoModel
    ) -> tuple[type[OntoModel], Any]:
        mapper_identity = entity_type.identity_field
        value = getattr(instance, mapper_identity)
        return (entity_type, value)

    def register(self, instance: OntoModel) -> None:
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if identity is None:
            return
        key = (entity_type, identity)
        self.identity_map[key] = instance
        self.snapshots[id(instance)] = instance.model_dump()

    def get_cached(self, entity_type: type[OntoModel], identity: Any) -> OntoModel | None:
        return self.identity_map.get((entity_type, identity))

    def expire(self, entity_type: type[OntoModel], identity: Any) -> None:
        key = (entity_type, identity)
        instance = self.identity_map.pop(key, None)
        if instance is not None:
            self.snapshots.pop(id(instance), None)

    def clear_pending(self) -> None:
        self.pending.clear()
