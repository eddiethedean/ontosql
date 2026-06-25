"""Graph sync public API."""

from __future__ import annotations

from typing import Any

from triplemodel import Store

from ontosql.semantic.model import OntoModel
from ontosql.sync.graph import GraphSyncMode, sync_instance_to_store
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


def push_instance(
    instance: OntoModel,
    target: GraphSyncTarget | Store,
    *,
    mode: GraphSyncMode = "patch",
    mapper_cls: type[Any] | None = None,
    registry: Any | None = None,
) -> None:
    """Push a semantic instance into a graph sync target."""
    if isinstance(target, Store):
        sync_instance_to_store(
            instance,
            target,
            mode=mode,
            mapper_cls=mapper_cls,
            registry=registry,
        )
        return

    scratch = Store()
    sync_instance_to_store(
        instance,
        scratch,
        mode=mode,
        mapper_cls=mapper_cls,
        registry=registry,
    )
    from triplemodel.store.terms import term_str

    remove_store = Store()
    subjects = {term_str(t[0]) for t in scratch}
    for triple in target.graph:
        if term_str(triple[0]) in subjects:
            remove_store.add(triple)
    target.update_graph(add=scratch, remove=remove_store)


def replace_subject(
    instance: OntoModel,
    target: GraphSyncTarget | Store,
    **kwargs: Any,
) -> None:
    """Replace the subject subgraph for an instance."""
    push_instance(instance, target, mode="replace", **kwargs)


def patch_subject(
    instance: OntoModel,
    target: GraphSyncTarget | Store,
    **kwargs: Any,
) -> None:
    """Patch owned predicates for an instance."""
    push_instance(instance, target, mode="patch", **kwargs)


__all__ = [
    "GraphSyncMode",
    "StoreSyncTarget",
    "patch_subject",
    "push_instance",
    "replace_subject",
    "sync_instance_to_store",
]
