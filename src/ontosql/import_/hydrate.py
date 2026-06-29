"""Hydrate OntoModel instances from RDF graphs using mapper metadata."""

from __future__ import annotations

from typing import Any, get_args, get_origin

from pydantic import ValidationError
from pyoxigraph import Literal, NamedNode
from triplemodel import RDF_TYPE, Store

from ontosql.rdf.literals import (
    coerce_literal,
    expand_datatype,
    literal_matches_meta,
    pick_literal,
    scalar_type,
)
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, parse_iri_id
from ontosql.semantic.rdf_util import predicate_iri, resolve_prefix_registry

DEFAULT_MAX_NESTING_DEPTH = 32


class OntoImportError(Exception):
    """Raised when RDF cannot be mapped to a semantic instance."""


def _resolve_registry(
    mapper_cls: type[Any],
    registry: PrefixRegistry | None,
) -> PrefixRegistry:
    return resolve_prefix_registry(registry)


def _predicate_iri(
    model_cls: type[OntoModel],
    field_name: str,
    registry: PrefixRegistry,
) -> str | None:
    return predicate_iri(model_cls, field_name, registry)


def _objects_for_predicate(
    graph: Store,
    subject: NamedNode,
    predicate_iri: str,
) -> list[Any]:
    pred = NamedNode(predicate_iri)
    return list(graph.objects(subject, pred))


def _scalar_type(py_type: Any) -> Any:
    return scalar_type(py_type)


def _is_collection_type(py_type: Any) -> bool:
    origin = get_origin(py_type)
    return origin in (list, tuple, set, frozenset)


def _collection_item_type(py_type: Any) -> Any:
    origin = get_origin(py_type)
    if origin in (list, tuple, set, frozenset):
        args = get_args(py_type)
        if args:
            return args[0]
    return str


# Backward-compatible aliases for tests
def _coerce_literal(
    term: Any,
    *,
    py_type: Any,
    registry: PrefixRegistry,
    meta: dict[str, Any],
) -> Any:
    return coerce_literal(
        term, py_type=py_type, registry=registry, meta=meta, error_type=OntoImportError
    )


def _pick_literal(objects: list[Any], meta: dict[str, Any], registry: PrefixRegistry) -> Any:
    return pick_literal(objects, meta, registry, error_type=OntoImportError)


_expand_datatype = expand_datatype
_literal_matches_meta = literal_matches_meta


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
        return coerce_literal(
            term, py_type=py_type, registry=registry, meta={}, error_type=OntoImportError
        )
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
    mapper: type[Any],
    *,
    iri: str | None = None,
    registry: PrefixRegistry | None = None,
    max_nesting_depth: int = DEFAULT_MAX_NESTING_DEPTH,
    _depth: int = 0,
    _visited: set[str] | None = None,
) -> OntoModel:
    """Hydrate a semantic instance from triples using mapper metadata."""
    reg = _resolve_registry(mapper, registry)
    entity_type: type[OntoModel] = mapper.entity

    if iri is None:
        raise OntoImportError("graph_to_instance requires iri=")

    if _depth > max_nesting_depth:
        raise OntoImportError(f"Nested RDF depth exceeds max_nesting_depth={max_nesting_depth}")

    visited = _visited if _visited is not None else set()
    if iri in visited:
        raise OntoImportError(f"Circular nested reference at {iri!r}")
    visited.add(iri)

    subject = NamedNode(iri)
    _validate_type(graph, subject, entity_type, reg)

    fields: dict[str, Any] = {}

    for field_name, _cmap in mapper.column_maps.items():
        if field_name in mapper.nested_maps:
            continue
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None and field_name != mapper.identity_field:
            continue
        if field_name == mapper.identity_field:
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
        if _is_collection_type(py_type):
            item_type = _collection_item_type(py_type)
            values: list[Any] = []
            seen: set[Any] = set()
            for obj in objects:
                term = pick_literal(
                    objects=[obj], meta=meta, registry=reg, error_type=OntoImportError
                )
                value = coerce_literal(
                    term, py_type=item_type, registry=reg, meta=meta, error_type=OntoImportError
                )
                if value not in seen:
                    seen.add(value)
                    values.append(value)
            fields[field_name] = values
        else:
            if len(objects) > 1:
                raise OntoImportError(
                    f"Scalar field {field_name!r} has {len(objects)} values; expected one"
                )
            term = pick_literal(objects, meta, reg, error_type=OntoImportError)
            fields[field_name] = coerce_literal(
                term, py_type=py_type, registry=reg, meta=meta, error_type=OntoImportError
            )

    for field_name, nmap in mapper.nested_maps.items():
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
                max_nesting_depth=max_nesting_depth,
                _depth=_depth + 1,
                _visited=visited,
            )
        elif isinstance(obj, Literal):
            raise OntoImportError(f"Nested field {field_name!r} expects a URI object, got Literal")
        else:
            raise OntoImportError(
                f"Nested field {field_name!r} expects a URI object, got {type(obj).__name__}"
            )

    for field_name, cmap in mapper.collection_maps.items():
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None:
            continue
        objects = _objects_for_predicate(graph, subject, predicate)
        if not objects:
            fields[field_name] = []
            continue
        items: list[Any] = []
        seen_iris: set[str] = set()
        for obj in objects:
            if isinstance(obj, NamedNode):
                from triplemodel.store.terms import term_str

                nested_iri = term_str(obj)
                if nested_iri in seen_iris:
                    continue
                seen_iris.add(nested_iri)
                items.append(
                    graph_to_instance(
                        graph,
                        cmap.nested_mapper,
                        iri=nested_iri,
                        registry=reg,
                        max_nesting_depth=max_nesting_depth,
                        _depth=_depth + 1,
                        _visited=visited,
                    )
                )
            else:
                raise OntoImportError(
                    f"Collection {field_name!r} expects URI objects, got {type(obj).__name__}"
                )
        fields[field_name] = items

    try:
        return entity_type.model_validate(fields)
    except ValidationError as exc:
        raise OntoImportError(f"Cannot validate {entity_type.__name__} from RDF: {exc}") from exc


def subject_iri_from_jsonld(doc: dict[str, Any]) -> str:
    """Extract @id from a JSON-LD document."""
    iri = doc.get("@id")
    if not isinstance(iri, str):
        raise OntoImportError("JSON-LD document requires @id")
    return iri
