"""Hydrate OntoModel instances from RDF graphs using mapper metadata."""

from __future__ import annotations

from typing import Any

from pyoxigraph import Literal, NamedNode
from triplemodel import RDF_TYPE, Store

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, parse_iri_id


class OntoImportError(Exception):
    """Raised when RDF cannot be mapped to a semantic instance."""


def _resolve_registry(
    mapper_cls: type[Any],
    registry: PrefixRegistry | None,
) -> PrefixRegistry:
    if registry is not None:
        return registry
    entity_registry = mapper_cls.entity.registry
    if entity_registry is not None:
        return entity_registry
    return PrefixRegistry()


def _predicate_iri(
    model_cls: type[OntoModel],
    field_name: str,
    registry: PrefixRegistry,
) -> str | None:
    from ontosql.semantic.model import get_onto_property_meta

    meta = get_onto_property_meta(model_cls, field_name)
    explicit = meta.get("iri")
    if isinstance(explicit, str):
        return explicit
    curie = meta.get("ontology")
    if isinstance(curie, str):
        return registry.expand(curie)
    return None


def _objects_for_predicate(
    graph: Store,
    subject: NamedNode,
    predicate_iri: str,
) -> list[Any]:
    pred = NamedNode(predicate_iri)
    return list(graph.objects(subject, pred))


def _coerce_literal(
    term: Any,
    *,
    py_type: Any,
    registry: PrefixRegistry,
    meta: dict[str, Any],
) -> Any:
    if isinstance(term, NamedNode):
        return str(term)
    if not isinstance(term, Literal):
        return str(term)
    raw = str(term.value)
    if py_type is bool:
        return raw.lower() in ("true", "1")
    if py_type is int:
        return int(raw)
    if py_type is float:
        return float(raw)
    return raw


def _coerce_identity(
    term: Any,
    model_cls: type[OntoModel],
    *,
    registry: PrefixRegistry,
) -> Any:
    from triplemodel.store.terms import term_str

    if isinstance(term, NamedNode):
        iri = term_str(term)
        parsed = parse_iri_id(iri, model_cls)
        if parsed is not None:
            return parsed
        return iri
    if isinstance(term, Literal):
        identity_field = model_cls.identity_field
        field_info = model_cls.model_fields.get(identity_field)
        py_type = field_info.annotation if field_info else str
        return _coerce_literal(term, py_type=py_type, registry=registry, meta={})
    return term


def _validate_type(
    graph: Store,
    subject: NamedNode,
    entity_type: type[OntoModel],
    registry: PrefixRegistry,
) -> None:
    type_iri = entity_type.type_iri
    if not type_iri:
        return
    expected = NamedNode(registry.expand(type_iri))
    actual = graph.objects(subject, NamedNode(RDF_TYPE))
    if expected not in actual:
        raise OntoImportError(
            f"Subject {subject!s} does not have rdf:type {registry.expand(type_iri)!r} "
            f"required by {entity_type.__name__}."
        )


def graph_to_instance(
    graph: Store,
    mapper_cls: type[Any],
    *,
    iri: str | None = None,
    registry: PrefixRegistry | None = None,
) -> OntoModel:
    """Hydrate a semantic instance from triples using mapper metadata."""
    reg = _resolve_registry(mapper_cls, registry)
    entity_type: type[OntoModel] = mapper_cls.entity

    if iri is None:
        raise OntoImportError("graph_to_instance requires iri=")

    subject = NamedNode(iri)
    _validate_type(graph, subject, entity_type, reg)

    fields: dict[str, Any] = {}

    for field_name, _cmap in mapper_cls.column_maps.items():
        if field_name in mapper_cls.nested_maps:
            continue
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None and field_name != mapper_cls.identity_field:
            continue
        if field_name == mapper_cls.identity_field:
            parsed = parse_iri_id(iri, entity_type)
            if parsed is not None:
                fields[field_name] = parsed
                continue
        if predicate is None:
            continue
        objects = _objects_for_predicate(graph, subject, predicate)
        if not objects:
            continue
        field_info = entity_type.model_fields.get(field_name)
        py_type = field_info.annotation if field_info else str
        from ontosql.semantic.model import get_onto_property_meta

        meta = get_onto_property_meta(entity_type, field_name)
        fields[field_name] = _coerce_literal(objects[0], py_type=py_type, registry=reg, meta=meta)

    for field_name, nmap in mapper_cls.nested_maps.items():
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None:
            continue
        objects = _objects_for_predicate(graph, subject, predicate)
        if not objects:
            fields[field_name] = None
            continue
        obj = objects[0]
        if isinstance(obj, NamedNode):
            from triplemodel.store.terms import term_str

            nested_iri = term_str(obj)
            fields[field_name] = graph_to_instance(
                graph,
                nmap.nested_mapper,
                iri=nested_iri,
                registry=reg,
            )
        else:
            fields[field_name] = None

    return entity_type.model_construct(**fields)


def subject_iri_from_jsonld(doc: dict[str, Any]) -> str:
    """Extract @id from a JSON-LD document."""
    iri = doc.get("@id")
    if not isinstance(iri, str):
        raise OntoImportError("JSON-LD document requires @id")
    return iri
