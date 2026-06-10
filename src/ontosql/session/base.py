"""Shared session logic."""

from __future__ import annotations

from typing import Any

from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.state import SessionState


class SessionBase:
    """Base for sync and async OntoSQL sessions."""

    def __init__(
        self,
        maps: list[type[Any]] | None = None,
        *,
        registry: MapperRegistry | None = None,
    ) -> None:
        self._registry = registry or MapperRegistry()
        if maps:
            self._registry.register_many(maps)
        self._state = SessionState()

    def _mapper_for(self, entity_type: type[Any]) -> type[Any]:
        return self._registry.get(entity_type)

    def _is_new_instance(self, mapper_cls: type[Any], instance: OntoModel) -> bool:
        identity = getattr(instance, mapper_cls.identity_field, None)
        if identity is None:
            return True
        return not (
            id(instance) in self._state.snapshots
            or self._state.get_cached(type(instance), identity) is not None
        )

    def expire(self, entity_type: type[Any], *, id: Any) -> None:
        """Evict an instance from the identity map."""
        if not issubclass(entity_type, OntoModel):
            raise TypeError(f"entity_type must be an OntoModel subclass, got {entity_type!r}")
        self._state.expire(entity_type, id)

    def rollback_pending(self) -> None:
        """Discard queued save/delete plans without touching the database."""
        self._state.clear_pending()
