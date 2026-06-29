"""Graph sync public API."""

from __future__ import annotations

from typing import Any

from triplemodel import Store

from ontosql.semantic.model import OntoModel
from ontosql.sync.graph import GraphSyncMode, sync_instance_to_store
from ontosql.sync.materialize import materialize_find, materialize_find_async
from ontosql.sync.target import GraphSyncTarget


class StoreSyncTarget:
    """In-memory graph sync target backed by a TripleModel Store."""

    def __init__(self, store: Store | None = None) -> None:
        self._store = store or Store()

    @property
    def graph(self) -> Store:
        return self._store

    def update_graph(
        self,
        *,
        add: Store | None = None,
        remove: Store | None = None,
    ) -> None:
        if remove is not None:
            for triple in remove:
                self._store.remove(triple)
        if add is not None:
            for triple in add:
                self._store.add(triple)


def _target_store(target: GraphSyncTarget | Store) -> Store:
    if isinstance(target, Store):
        return target
    return target.graph


def push_instance(
    instance: OntoModel,
    target: GraphSyncTarget | Store,
    *,
    mapper: type[Any],
    mode: GraphSyncMode = "patch",
    registry: Any | None = None,
    prior_nested_iris: set[str] | None = None,
) -> None:
    """Push a semantic instance into a graph sync target."""
    from ontosql.sync.graph import sync_instance_to_store

    sync_instance_to_store(
        instance,
        _target_store(target),
        mode=mode,
        mapper_cls=mapper,
        registry=registry,
        prior_nested_iris=prior_nested_iris,
    )


def remove_instance(
    instance: OntoModel,
    target: GraphSyncTarget | Store,
    *,
    mapper: type[Any],
    registry: Any | None = None,
) -> None:
    """Remove an instance subgraph from a graph sync target."""
    from ontosql.sync.graph import remove_instance_from_store

    remove_instance_from_store(
        instance,
        _target_store(target),
        mapper_cls=mapper,
        registry=registry,
    )


__all__ = [
    "GraphSyncMode",
    "GraphSyncTarget",
    "StoreSyncTarget",
    "materialize_find",
    "materialize_find_async",
    "push_instance",
    "remove_instance",
    "sync_instance_to_store",
]
