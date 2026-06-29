"""Read-only graph materialization from OntoSession results."""

from __future__ import annotations

from typing import Any

from triplemodel import Store

from ontosql.export.instance import instances_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel


def materialize_entity(
    instance: OntoModel,
    *,
    registry: PrefixRegistry | None = None,
) -> Store:
    """Build a Store containing one semantic instance subgraph."""
    return instances_to_graph([instance], registry=registry)


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
    return instances_to_graph(instances, registry=registry)
