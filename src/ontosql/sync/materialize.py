"""Read-only graph materialization from OntoSession results."""

from __future__ import annotations

from typing import Any

from triplemodel import Store, bind_namespaces

from ontosql.export.instance import instance_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel


def materialize_entity(
    instance: OntoModel,
    *,
    registry: PrefixRegistry | None = None,
) -> Store:
    """Build a Store containing one semantic instance subgraph."""
    return instance_to_graph(instance, registry=registry)


def materialize_find(
    session: Any,
    entity_type: type[OntoModel],
    *,
    where: Any | None = None,
    order_by: Any | None = None,
    limit: int | None = None,
    offset: int | None = None,
    registry: PrefixRegistry | None = None,
) -> Store:
    """Materialize find() results as a merged RDF graph."""
    instances = session.find(
        entity_type,
        where=where,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    merged = Store()
    reg = registry
    if reg is not None:
        bind_namespaces(merged, reg.prefixes())
    visited: set[int] = set()
    for instance in instances:
        subgraph = instance_to_graph(instance, registry=reg, visited=visited)
        for triple in subgraph:
            merged.add(triple)
    return merged
