"""Shared RDF metadata helpers for export, import, sync, and SHACL."""

from __future__ import annotations

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, get_onto_property_meta


def resolve_prefix_registry(registry: PrefixRegistry | None = None) -> PrefixRegistry:
    """Return an explicit registry or a fresh default."""
    return registry or PrefixRegistry()


def predicate_iri(
    model_cls: type[OntoModel],
    field_name: str,
    registry: PrefixRegistry,
) -> str | None:
    """Resolve the RDF predicate IRI for a semantic field."""
    meta = get_onto_property_meta(model_cls, field_name)
    explicit = meta.get("iri")
    if isinstance(explicit, str):
        return explicit
    curie = meta.get("ontology")
    if isinstance(curie, str):
        return registry.expand(curie)
    return None
