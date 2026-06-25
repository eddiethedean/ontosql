"""Parse RDF payloads into TripleModel stores."""

from __future__ import annotations

import json
from typing import Any

from pyoxigraph import NamedNode
from triplemodel import RDF_TYPE, Store, bind_namespaces

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel


def load_graph(
    data: str | bytes,
    *,
    format: str = "turtle",
    registry: PrefixRegistry | None = None,
) -> Store:
    """Parse RDF text into a Store."""
    graph = Store()
    if registry is not None:
        bind_namespaces(graph, registry.prefixes())
    graph.parse(data, format=format)
    return graph


def load_graph_from_jsonld(
    doc: dict[str, Any],
    *,
    registry: PrefixRegistry | None = None,
) -> Store:
    """Parse a JSON-LD document dict into a Store."""
    payload = json.dumps(doc)
    return load_graph(payload, format="json-ld", registry=registry)


def find_subjects_by_type(
    graph: Store,
    type_iri: str,
    registry: PrefixRegistry,
) -> list[str]:
    """Return subject IRIs with the given rdf:type."""
    from triplemodel.store.terms import term_str

    expected = NamedNode(registry.expand(type_iri))
    type_node = NamedNode(RDF_TYPE)
    subjects: list[str] = []
    for triple in graph:
        if triple[1] == type_node and triple[2] == expected:
            subjects.append(term_str(triple[0]))
    return subjects


def resolve_mapper_registry(
    mapper_cls: type[Any],
    registry: PrefixRegistry | None,
) -> PrefixRegistry:
    if registry is not None:
        return registry
    entity: type[OntoModel] = mapper_cls.entity
    if entity.registry is not None:
        return entity.registry
    return PrefixRegistry()
