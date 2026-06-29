"""Entity I/O — JSON-LD and RDF import/export without OntoModel façade methods."""

from __future__ import annotations

from typing import Any

from ontosql.export.instance import instance_to_jsonld, instance_to_rdf
from ontosql.import_ import import_from_jsonld
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel


def to_jsonld(instance: OntoModel, *, registry: PrefixRegistry | None = None) -> dict[str, Any]:
    """Export a semantic instance as a JSON-LD document dict."""
    return instance_to_jsonld(instance, registry=registry)


def to_rdf(
    instance: OntoModel,
    *,
    format: str = "turtle",
    registry: PrefixRegistry | None = None,
) -> str:
    """Export a semantic instance as an RDF serialization string."""
    return instance_to_rdf(instance, format=format, registry=registry)


def from_jsonld(
    entity_type: type[OntoModel],
    doc: dict[str, Any],
    *,
    mapper: type[Any],
    registry: PrefixRegistry | None = None,
) -> OntoModel:
    """Hydrate an instance from a JSON-LD document using a mapper."""
    instance = import_from_jsonld(doc, mapper, registry=registry)
    if not isinstance(instance, entity_type):
        raise TypeError(f"Expected {entity_type.__name__}, got {type(instance).__name__}")
    return instance
