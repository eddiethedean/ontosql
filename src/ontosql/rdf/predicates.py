"""RDF predicate metadata derived from mapper classes."""

from __future__ import annotations

from typing import Any

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel
from ontosql.semantic.rdf_util import predicate_iri


def owned_predicates(mapper_cls: type[Any], registry: PrefixRegistry) -> frozenset[str]:
    """Predicates owned by a mapper for patch/replace sync."""
    entity_type: type[OntoModel] = mapper_cls.entity
    preds: set[str] = set()
    type_iri = entity_type.type_iri
    if type_iri:
        preds.add(registry.expand(type_iri))
    for field_name in mapper_cls.column_maps:
        if field_name in mapper_cls.nested_maps:
            continue
        pred = predicate_iri(entity_type, field_name, registry)
        if pred:
            preds.add(pred)
    for field_name in mapper_cls.nested_maps:
        pred = predicate_iri(entity_type, field_name, registry)
        if pred:
            preds.add(pred)
    for field_name in mapper_cls.collection_maps:
        pred = predicate_iri(entity_type, field_name, registry)
        if pred:
            preds.add(pred)
    return frozenset(preds)
