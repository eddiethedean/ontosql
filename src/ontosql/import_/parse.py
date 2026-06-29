"""Parse RDF payloads into TripleModel stores."""

from __future__ import annotations

import json
from typing import Any

from pyoxigraph import NamedNode
from triplemodel import RDF_TYPE, Store, bind_namespaces

from ontosql.import_.hydrate import OntoImportError
from ontosql.registry import PrefixRegistry
from ontosql.semantic.rdf_util import resolve_prefix_registry

# Suggested caps when ``untrusted=True`` (API boundary for public import endpoints).
UNTRUSTED_DEFAULT_MAX_BYTES = 1_048_576
UNTRUSTED_DEFAULT_MAX_TRIPLES = 100_000


def load_graph(
    data: str | bytes,
    *,
    format: str = "turtle",
    registry: PrefixRegistry | None = None,
    max_bytes: int | None = None,
    max_triples: int | None = None,
    untrusted: bool = False,
) -> Store:
    """Parse RDF text into a Store.

    Optional ``max_bytes`` and ``max_triples`` guard untrusted payloads (raises
    ``OntoImportError`` when exceeded).

    When ``untrusted=True``, applies ``UNTRUSTED_DEFAULT_MAX_BYTES`` and
    ``UNTRUSTED_DEFAULT_MAX_TRIPLES`` for any limit not explicitly set.

    **Note:** ``max_triples`` is checked **after** ``graph.parse()`` completes.
    A small payload can still expand during parsing (blank-node chains, JSON-LD
    expansion). Always set ``max_bytes`` and rate-limit import endpoints; do not
    rely on ``max_triples`` alone for DoS protection.
    """
    if untrusted:
        if max_bytes is None:
            max_bytes = UNTRUSTED_DEFAULT_MAX_BYTES
        if max_triples is None:
            max_triples = UNTRUSTED_DEFAULT_MAX_TRIPLES
    if isinstance(data, str):
        text = data
        raw = data.encode("utf-8")
    else:
        raw = data
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OntoImportError("Invalid UTF-8 in RDF payload") from exc
    if max_bytes is not None and len(raw) > max_bytes:
        raise OntoImportError(f"RDF payload exceeds max_bytes={max_bytes} (got {len(raw)} bytes)")
    graph = Store()
    if registry is not None:
        bind_namespaces(graph, registry.prefixes())
    graph.parse(text, format=format)
    if max_triples is not None and len(graph) > max_triples:
        raise OntoImportError(
            f"RDF graph exceeds max_triples={max_triples} (got {len(graph)} triples)"
        )
    return graph


def load_graph_from_jsonld(
    doc: dict[str, Any],
    *,
    registry: PrefixRegistry | None = None,
    max_bytes: int | None = None,
    max_triples: int | None = None,
    untrusted: bool = False,
) -> Store:
    """Parse a JSON-LD document dict into a Store."""
    payload = json.dumps(doc)
    return load_graph(
        payload,
        format="json-ld",
        registry=registry,
        max_bytes=max_bytes,
        max_triples=max_triples,
        untrusted=untrusted,
    )


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
    return resolve_prefix_registry(registry)
