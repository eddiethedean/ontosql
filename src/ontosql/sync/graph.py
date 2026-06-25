"""Subject-scoped graph sync from OntoModel instances."""

from __future__ import annotations

from typing import Any, Literal

from pyoxigraph import NamedNode
from triplemodel import Store
from triplemodel.io.sync.predicate_ops import remove_triples_for_predicates
from triplemodel.store.terms import term_str

from ontosql.export.instance import instance_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, get_onto_property_meta

GraphSyncMode = Literal["add", "replace", "patch"]


def _resolve_registry(instance: OntoModel, registry: PrefixRegistry | None) -> PrefixRegistry:
    if registry is not None:
        return registry
    model_registry = type(instance).registry
    if model_registry is not None:
        return model_registry
    return PrefixRegistry()


def _predicate_iri_for_field(
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
        pred = _predicate_iri_for_field(entity_type, field_name, registry)
        if pred:
            preds.add(pred)
    for field_name in mapper_cls.nested_maps:
        pred = _predicate_iri_for_field(entity_type, field_name, registry)
        if pred:
            preds.add(pred)
    return frozenset(preds)


def _subjects_in_graph(graph: Store) -> set[str]:
    from triplemodel.store.terms import term_str

    return {term_str(triple[0]) for triple in graph}


def _remove_all_subject_triples(target: Store, subject_iri: str) -> None:
    subject = NamedNode(subject_iri)
    for triple in list(target.triples((subject, None, None))):
        target.remove(triple)


def _add_graph_triples(target: Store, source: Store) -> None:
    for triple in source:
        target.add(triple)


def sync_instance_to_store(
    instance: OntoModel,
    target: Store,
    *,
    mode: GraphSyncMode = "patch",
    registry: PrefixRegistry | None = None,
    mapper_cls: type[Any] | None = None,
) -> Store:
    """Write a semantic instance subgraph into target using sync semantics."""
    from ontosql.mapping.registry import MapperRegistry

    reg = _resolve_registry(instance, registry)
    if mapper_cls is None:
        mapper_cls = MapperRegistry().get(type(instance))

    new_graph = instance_to_graph(instance, registry=reg)
    subjects = _subjects_in_graph(new_graph)

    if mode == "add":
        _add_graph_triples(target, new_graph)
        return target

    if mode == "replace":
        for subject_iri in subjects:
            _remove_all_subject_triples(target, subject_iri)
        _add_graph_triples(target, new_graph)
        return target

    if mode == "patch":
        owned = owned_predicates(mapper_cls, reg)
        root_iri = next(iter(subjects)) if subjects else None
        if root_iri is not None:
            remove_triples_for_predicates(target, NamedNode(root_iri), set(owned))
            for triple in new_graph:
                if term_str(triple[0]) == root_iri:
                    target.add(triple)

        nested_subjects = subjects - {root_iri} if root_iri else subjects
        for nested_iri in nested_subjects:
            _remove_all_subject_triples(target, nested_iri)
            for triple in new_graph:
                if term_str(triple[0]) == nested_iri:
                    target.add(triple)
        return target

    return target
