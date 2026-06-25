"""Subject-scoped graph sync from OntoModel instances."""

from __future__ import annotations

from typing import Any, Literal

from pyoxigraph import NamedNode
from triplemodel import Store
from triplemodel.io.sync.predicate_ops import remove_triples_for_predicates
from triplemodel.store.terms import term_str

from ontosql.export.instance import instance_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, build_instance_iri, get_onto_property_meta

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
    return {term_str(triple[0]) for triple in graph}


def _remove_all_subject_triples(target: Store, subject_iri: str) -> None:
    subject = NamedNode(subject_iri)
    for triple in list(target.triples((subject, None, None))):
        target.remove(triple)


def _add_graph_triples(target: Store, source: Store) -> None:
    for triple in source:
        target.add(triple)


def _nested_mapper_for_iri(
    instance: OntoModel,
    mapper_cls: type[Any],
    nested_iri: str,
    registry: PrefixRegistry,
) -> type[Any] | None:
    for field_name, nmap in mapper_cls.nested_maps.items():
        nested_value = getattr(instance, field_name, None)
        if nested_value is not None and build_instance_iri(nested_value, registry) == nested_iri:
            return nmap.nested_mapper
    return None


def _patch_subject_in_store(
    target: Store,
    new_graph: Store,
    subject_iri: str,
    owned: frozenset[str],
) -> None:
    remove_triples_for_predicates(target, NamedNode(subject_iri), set(owned))
    for triple in new_graph:
        if term_str(triple[0]) == subject_iri:
            target.add(triple)


def _sync_nested_subjects(
    target: Store,
    new_graph: Store,
    instance: OntoModel,
    mapper_cls: type[Any],
    nested_subjects: set[str],
    registry: PrefixRegistry,
) -> None:
    """Patch nested subjects by owned predicates only (preserves shared nested nodes)."""
    for nested_iri in nested_subjects:
        nested_mapper = _nested_mapper_for_iri(instance, mapper_cls, nested_iri, registry)
        if nested_mapper is not None:
            owned = owned_predicates(nested_mapper, registry)
            _patch_subject_in_store(target, new_graph, nested_iri, owned)
        else:
            _remove_all_subject_triples(target, nested_iri)
            for triple in new_graph:
                if term_str(triple[0]) == nested_iri:
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
    root_iri = build_instance_iri(instance, reg)
    nested_subjects = subjects - {root_iri}

    if mode == "add":
        _add_graph_triples(target, new_graph)
        return target

    if mode == "replace":
        if root_iri in subjects:
            _remove_all_subject_triples(target, root_iri)
            for triple in new_graph:
                if term_str(triple[0]) == root_iri:
                    target.add(triple)
        _sync_nested_subjects(target, new_graph, instance, mapper_cls, nested_subjects, reg)
        return target

    if mode == "patch":
        if root_iri in subjects:
            owned = owned_predicates(mapper_cls, reg)
            _patch_subject_in_store(target, new_graph, root_iri, owned)
        _sync_nested_subjects(target, new_graph, instance, mapper_cls, nested_subjects, reg)
        return target

    raise ValueError(f"Unknown graph sync mode: {mode!r}")


def remove_instance_from_store(
    instance: OntoModel,
    target: Store,
    *,
    registry: PrefixRegistry | None = None,
    mapper_cls: type[Any] | None = None,
) -> Store:
    """Remove all triples for the root instance subject only (not shared nested nodes)."""
    reg = _resolve_registry(instance, registry)
    root_iri = build_instance_iri(instance, reg)
    _remove_all_subject_triples(target, root_iri)
    return target
