"""Shared session logic."""

from __future__ import annotations

from typing import Any

from triplemodel import Store

from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.graph_sync import flush_graph_sync
from ontosql.session.state import SessionState
from ontosql.sync.graph import GraphSyncMode
from ontosql.sync.target import GraphSyncTarget

GraphSyncTargetLike = GraphSyncTarget | Store


class SessionBase:
    """Base for sync and async OntoSQL sessions."""

    def __init__(
        self,
        maps: list[type[Any]] | None = None,
    ) -> None:
        self._registry = MapperRegistry()
        if maps:
            self._registry.register_many(maps)
        self._state = SessionState()
        self._graph_sync: GraphSyncTargetLike | None = None
        self._graph_sync_mode: GraphSyncMode = "patch"

    def _mapper_for(self, entity_type: type[Any]) -> type[Any]:
        return self._registry.get(entity_type)

    def _is_new_instance(self, mapper_cls: type[Any], instance: OntoModel) -> bool:
        identity = getattr(instance, mapper_cls.identity_field, None)
        if identity is None:
            return True
        entity_type = type(instance)
        key = (entity_type, identity)
        return not (
            key in self._state.snapshots
            or self._state.get_cached(entity_type, identity) is not None
        )

    def expire(self, entity_type: type[Any], *, identity: Any) -> None:
        """Evict an instance from the identity map."""
        if not issubclass(entity_type, OntoModel):
            raise TypeError(f"entity_type must be an OntoModel subclass, got {entity_type!r}")
        self._state.expire(entity_type, identity)

    def expire_all(self) -> None:
        """Evict all cached instances and snapshots from the identity map."""
        self._state.expire_all()

    def clear_pending(self) -> None:
        """Discard queued save/delete plans and graph sync queues without touching SQL.

        Does **not** roll back flushed writes or an open database transaction. Use
        ``session.rollback()`` on the underlying SQLAlchemy session for that, or
        exit the context manager with an exception to roll back uncommitted work.
        """
        self._state.clear_pending()
        self._state.clear_graph_sync()

    @property
    def graph_sync_pending(self) -> bool:
        """True when graph sync operations remain queued (e.g. after partial failure)."""
        return self._state.has_graph_sync_pending

    @property
    def graph_sync_failures(self) -> list[Any]:
        """Failures from the last ``flush_graph_sync`` attempt (after SQL commit)."""
        return list(self._state.graph_sync_failures)

    def retry_graph_sync(self) -> None:
        """Retry queued graph sync after a partial failure (SQL already committed)."""
        flush_graph_sync(
            self._state,
            self._graph_sync,
            mode=self._graph_sync_mode,
            mapper_for=self._mapper_for,
            registry=getattr(self, "_registry_prefix", None),
        )
