"""RDF import into OntoModel instances."""

from __future__ import annotations

from typing import Any

from ontosql.import_.hydrate import OntoImportError, graph_to_instance, subject_iri_from_jsonld
from ontosql.import_.parse import (
    find_subjects_by_type,
    load_graph,
    load_graph_from_jsonld,
    resolve_mapper_registry,
)
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel


def import_from_rdf(
    data: str | bytes,
    mapper_cls: type[Any],
    *,
    format: str = "turtle",
    iri: str | None = None,
    registry: PrefixRegistry | None = None,
    max_bytes: int | None = None,
    max_triples: int | None = None,
) -> OntoModel:
    """Hydrate a semantic instance from an RDF serialization."""
    reg = resolve_mapper_registry(mapper_cls, registry)
    graph = load_graph(
        data,
        format=format,
        registry=reg,
        max_bytes=max_bytes,
        max_triples=max_triples,
    )
    if iri is None:
        entity_type: type[OntoModel] = mapper_cls.entity
        type_iri = entity_type.type_iri
        if not type_iri:
            raise OntoImportError("import_from_rdf requires iri= when entity has no type_iri")
        subjects = find_subjects_by_type(graph, type_iri, reg)
        if len(subjects) != 1:
            raise OntoImportError(
                f"Expected exactly one subject for {type_iri!r}, found {len(subjects)}"
            )
        iri = subjects[0]
    return graph_to_instance(graph, mapper_cls, iri=iri, registry=reg)


def import_from_jsonld(
    doc: dict[str, Any],
    mapper_cls: type[Any],
    *,
    registry: PrefixRegistry | None = None,
    max_bytes: int | None = None,
    max_triples: int | None = None,
) -> OntoModel:
    """Hydrate a semantic instance from a JSON-LD document dict."""
    reg = resolve_mapper_registry(mapper_cls, registry)
    graph = load_graph_from_jsonld(
        doc,
        registry=reg,
        max_bytes=max_bytes,
        max_triples=max_triples,
    )
    iri = doc.get("@id")
    if not isinstance(iri, str):
        entity_type: type[OntoModel] = mapper_cls.entity
        type_iri = entity_type.type_iri
        if not type_iri:
            raise OntoImportError("import_from_jsonld requires @id when entity has no type_iri")
        subjects = find_subjects_by_type(graph, type_iri, reg)
        if len(subjects) != 1:
            raise OntoImportError(
                f"Expected exactly one subject for {type_iri!r}, found {len(subjects)}"
            )
        iri = subjects[0]
    return graph_to_instance(graph, mapper_cls, iri=iri, registry=reg)


__all__ = [
    "OntoImportError",
    "find_subjects_by_type",
    "graph_to_instance",
    "import_from_jsonld",
    "import_from_rdf",
    "load_graph",
    "load_graph_from_jsonld",
    "subject_iri_from_jsonld",
]
