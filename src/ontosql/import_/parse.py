"""Parse RDF payloads into TripleModel stores."""

from __future__ import annotations

import json
from typing import Any

from pyoxigraph import NamedNode
from triplemodel import RDF_TYPE, Store, bind_namespaces

from ontosql.import_.hydrate import OntoImportError
from ontosql.rdf.formats import normalize_format
from ontosql.registry import PrefixRegistry
from ontosql.semantic.rdf_util import resolve_prefix_registry

# Suggested caps when ``untrusted=True`` (API boundary for public import endpoints).
UNTRUSTED_DEFAULT_MAX_BYTES = 1_048_576
UNTRUSTED_DEFAULT_MAX_TRIPLES = 100_000


def _pyoxigraph_format(fmt: str) -> Any:
    from pyoxigraph import RdfFormat

    key = normalize_format(fmt)
    mapping = {
        "turtle": RdfFormat.TURTLE,
        "nt": RdfFormat.N_TRIPLES,
        "xml": RdfFormat.RDF_XML,
        "json-ld": RdfFormat.JSON_LD,
    }
    return mapping[key]


def _parse_into_store(
    graph: Store,
    text: str,
    *,
    format: str,
    max_triples: int | None,
) -> None:
    """Parse RDF text into graph, enforcing max_triples incrementally when set."""
    if max_triples is None:
        graph.parse(text, format=format)
        return
    from pyoxigraph import parse

    for count, quad in enumerate(parse(text, format=_pyoxigraph_format(format)), start=1):
        graph.add((quad.subject, quad.predicate, quad.object))
        if count > max_triples:
            raise OntoImportError(
                f"RDF graph exceeds max_triples={max_triples} during parse"
            )


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

    When ``max_triples`` is set, parsing stops as soon as the cap is exceeded
    (incremental enforcement). Without ``max_triples``, the full graph is
    parsed before return — pair with ``max_bytes`` on untrusted inputs.
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
    _parse_into_store(graph, text, format=format, max_triples=max_triples)
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
