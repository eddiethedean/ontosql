"""Generate SHACL NodeShapes from OntoMapper metadata."""

from __future__ import annotations

from typing import Any, get_args, get_origin

from pyoxigraph import Literal, NamedNode
from triplemodel import Store

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, get_onto_property_meta

SH = "http://www.w3.org/ns/shacl#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"

_PYTHON_TO_XSD: dict[type, str] = {
    str: f"{XSD}string",
    int: f"{XSD}integer",
    float: f"{XSD}double",
    bool: f"{XSD}boolean",
}


def _shape_iri(mapper_cls: type[Any], registry: PrefixRegistry) -> str:
    entity = mapper_cls.entity
    type_iri = entity.type_iri or entity.__name__
    expanded = registry.expand(type_iri) if ":" in type_iri else type_iri
    return f"{expanded}Shape"


def _predicate_iri(
    model_cls: type[OntoModel],
    field_name: str,
    registry: PrefixRegistry,
) -> str | None:
    meta = get_onto_property_meta(model_cls, field_name)
    explicit = meta.get("iri")
    if isinstance(explicit, str):
        return explicit
    curie = meta.get("ontology")
    if isinstance(curie, str):
        return registry.expand(curie)
    return None


def _python_type_to_xsd(annotation: Any) -> str | None:
    if annotation is None:
        return None
    origin = get_origin(annotation)
    if origin is not None:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return _python_type_to_xsd(args[0])
        return None
    if isinstance(annotation, type):
        return _PYTHON_TO_XSD.get(annotation)
    return None


def shapes_from_mapper(
    mapper_cls: type[Any],
    *,
    registry: PrefixRegistry | None = None,
    visited: set[type[Any]] | None = None,
) -> Store:
    """Build SHACL shapes for a mapper and nested mappers."""
    reg = registry or PrefixRegistry()
    seen = visited or set()
    if mapper_cls in seen:
        return Store()
    seen.add(mapper_cls)

    graph = Store()
    entity_type: type[OntoModel] = mapper_cls.entity
    shape = NamedNode(_shape_iri(mapper_cls, reg))
    graph.add((shape, NamedNode(f"{RDF}type"), NamedNode(f"{SH}NodeShape")))

    type_iri = entity_type.type_iri
    if type_iri:
        graph.add(
            (
                shape,
                NamedNode(f"{SH}targetClass"),
                NamedNode(reg.expand(type_iri)),
            )
        )

    for field_name in mapper_cls.column_maps:
        if field_name in mapper_cls.nested_maps:
            continue
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None:
            continue
        prop_shape = NamedNode(f"{_shape_iri(mapper_cls, reg)}/{field_name}")
        graph.add((shape, NamedNode(f"{SH}property"), prop_shape))
        graph.add((prop_shape, NamedNode(f"{RDF}type"), NamedNode(f"{SH}PropertyShape")))
        graph.add((prop_shape, NamedNode(f"{SH}path"), NamedNode(predicate)))

        field_info = entity_type.model_fields.get(field_name)
        meta = get_onto_property_meta(entity_type, field_name)
        datatype = meta.get("datatype")
        if isinstance(datatype, str):
            dt = reg.expand(datatype) if ":" in datatype and "://" not in datatype else datatype
        elif field_info is not None:
            dt = _python_type_to_xsd(field_info.annotation)
        else:
            dt = None
        if dt:
            graph.add((prop_shape, NamedNode(f"{SH}datatype"), NamedNode(dt)))

        optional = field_info is not None and (
            get_origin(field_info.annotation) is not None
            and type(None) in get_args(field_info.annotation)
        )
        min_count = "0" if optional else "1"
        graph.add(
            (
                prop_shape,
                NamedNode(f"{SH}minCount"),
                Literal(min_count, datatype=NamedNode(f"{XSD}integer")),
            )
        )

    for field_name, nmap in mapper_cls.nested_maps.items():
        predicate = _predicate_iri(entity_type, field_name, reg)
        if predicate is None:
            continue
        nested_shapes = shapes_from_mapper(nmap.nested_mapper, registry=reg, visited=seen)
        for triple in nested_shapes:
            graph.add(triple)

        prop_shape = NamedNode(f"{_shape_iri(mapper_cls, reg)}/{field_name}")
        graph.add((shape, NamedNode(f"{SH}property"), prop_shape))
        graph.add((prop_shape, NamedNode(f"{RDF}type"), NamedNode(f"{SH}PropertyShape")))
        graph.add((prop_shape, NamedNode(f"{SH}path"), NamedNode(predicate)))
        graph.add(
            (
                prop_shape,
                NamedNode(f"{SH}node"),
                NamedNode(_shape_iri(nmap.nested_mapper, reg)),
            )
        )
        xsd_int = NamedNode(f"{XSD}integer")
        graph.add((prop_shape, NamedNode(f"{SH}minCount"), Literal("0", datatype=xsd_int)))
        graph.add((prop_shape, NamedNode(f"{SH}maxCount"), Literal("1", datatype=xsd_int)))

    return graph


def shapes_from_mappers(
    mappers: list[type[Any]],
    *,
    registry: PrefixRegistry | None = None,
) -> Store:
    """Merge SHACL shapes for multiple mappers."""
    merged = Store()
    for mapper_cls in mappers:
        subgraph = shapes_from_mapper(mapper_cls, registry=registry)
        for triple in subgraph:
            merged.add(triple)
    return merged
