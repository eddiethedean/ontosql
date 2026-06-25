"""Export OntoModel instances to JSON-LD and RDF via TripleModel."""

from __future__ import annotations

import json
from typing import Any

from pyoxigraph import Literal, NamedNode
from triplemodel import RDF_TYPE, Store, bind_namespaces

from ontosql.export._formats import normalize_format
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import (
    OntoModel,
    build_instance_iri,
    get_onto_property_meta,
    iter_onto_fields,
)


def _resolve_registry(
    instance: OntoModel,
    registry: PrefixRegistry | None,
) -> PrefixRegistry:
    if registry is not None:
        return registry
    model_registry = type(instance).registry
    if model_registry is not None:
        return model_registry
    return PrefixRegistry()


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


def _literal_object(
    value: Any,
    *,
    registry: PrefixRegistry,
    meta: dict[str, Any] | None = None,
) -> Literal | NamedNode:
    if isinstance(value, str) and ("://" in value or value.startswith("urn:")):
        return NamedNode(value)
    if isinstance(value, bool):
        return Literal(value)
    datatype = meta.get("datatype") if meta else None
    language = meta.get("language") if meta else None
    if datatype is not None:
        is_curie = ":" in datatype and "://" not in datatype
        dt_iri = registry.expand(datatype) if is_curie else datatype
        return Literal(str(value), datatype=NamedNode(dt_iri))
    if language is not None:
        return Literal(str(value), language=language)
    return Literal(str(value))


def instance_to_graph(
    instance: OntoModel,
    *,
    registry: PrefixRegistry | None = None,
    visited: set[int] | None = None,
) -> Store:
    """Build a TripleModel graph from a semantic instance and its nested objects."""
    reg = _resolve_registry(instance, registry)
    graph = Store()
    bind_namespaces(graph, reg.prefixes())
    _write_instance(graph, instance, reg, visited=visited or set())
    return graph


def _write_instance(
    graph: Store,
    instance: OntoModel,
    registry: PrefixRegistry,
    *,
    visited: set[int],
) -> str:
    inst_key = id(instance)
    subject_iri = build_instance_iri(instance, registry)
    if inst_key in visited:
        return subject_iri
    visited.add(inst_key)

    subject = NamedNode(subject_iri)
    model_cls = type(instance)

    type_iri = model_cls.type_iri
    if type_iri:
        graph.add((subject, NamedNode(RDF_TYPE), NamedNode(registry.expand(type_iri))))

    for field_name, _field_info in iter_onto_fields(model_cls):
        value = getattr(instance, field_name, None)
        if value is None:
            continue
        predicate = _predicate_iri(model_cls, field_name, registry)
        if predicate is None:
            continue
        pred_node = NamedNode(predicate)
        field_meta = get_onto_property_meta(model_cls, field_name)

        if isinstance(value, OntoModel):
            nested_iri = _write_instance(graph, value, registry, visited=visited)
            graph.add((subject, pred_node, NamedNode(nested_iri)))
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                if isinstance(item, OntoModel):
                    nested_iri = _write_instance(graph, item, registry, visited=visited)
                    graph.add((subject, pred_node, NamedNode(nested_iri)))
                elif item is not None:
                    lit = _literal_object(item, registry=registry, meta=field_meta)
                    graph.add((subject, pred_node, lit))
        else:
            graph.add(
                (subject, pred_node, _literal_object(value, registry=registry, meta=field_meta))
            )

    return subject_iri


def instance_to_jsonld(
    instance: OntoModel,
    *,
    registry: PrefixRegistry | None = None,
) -> dict[str, Any]:
    """Serialize a semantic instance to a JSON-LD document dict."""
    reg = _resolve_registry(instance, registry)
    graph = instance_to_graph(instance, registry=reg)
    payload = json.loads(graph.serialize(format="json-ld"))
    if isinstance(payload, list) and len(payload) == 1:
        doc: dict[str, Any] = dict(payload[0])
    elif isinstance(payload, dict):
        doc = dict(payload)
    else:
        doc = {"@graph": payload}
    doc["@context"] = reg.context_dict()
    return doc


def instance_to_rdf(
    instance: OntoModel,
    *,
    format: str = "turtle",
    registry: PrefixRegistry | None = None,
) -> str:
    """Serialize a semantic instance to an RDF string."""
    reg = _resolve_registry(instance, registry)
    graph = instance_to_graph(instance, registry=reg)
    return graph.serialize(format=normalize_format(format))
