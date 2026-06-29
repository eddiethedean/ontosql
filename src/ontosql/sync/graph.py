"""Subject-scoped graph sync from OntoModel instances."""

from __future__ import annotations

from typing import Any, Literal

from pyoxigraph import NamedNode
from triplemodel import Store
from triplemodel.io.sync.predicate_ops import remove_triples_for_predicates
from triplemodel.store.terms import term_str

from ontosql.export.instance import instance_to_graph
from ontosql.rdf.predicates import owned_predicates
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, build_instance_iri
from ontosql.semantic.rdf_util import predicate_iri, resolve_prefix_registry

GraphSyncMode = Literal["add", "replace", "patch"]


def _resolve_registry(instance: OntoModel, registry: PrefixRegistry | None) -> PrefixRegistry:
    return resolve_prefix_registry(registry)


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
    for field_name, cmap in mapper_cls.collection_maps.items():
        items = getattr(instance, field_name, None) or []
        for item in items:
            if build_instance_iri(item, registry) == nested_iri:
                return cmap.nested_mapper
    return None


def _nested_iri_from_snapshot_item(
    nested_raw: dict[str, Any],
    nested_mapper: type[Any],
    registry: PrefixRegistry,
) -> str | None:
    nested_entity = nested_mapper.entity
    identity_field = nested_mapper.identity_field
    nested_id = nested_raw.get(identity_field)
    if nested_id is None:
        return None
    nested_data = {identity_field: nested_id}
    for key in nested_mapper.column_maps:
        if key in nested_raw:
            nested_data[key] = nested_raw[key]
    try:
        nested_instance = nested_entity.model_construct(**nested_data)
        return build_instance_iri(nested_instance, registry)
    except Exception:  # pragma: no cover
        return None


def nested_iris_from_snapshot(
    instance: OntoModel,
    mapper_cls: type[Any],
    snapshot: dict[str, Any] | None,
    registry: PrefixRegistry,
) -> set[str]:
    """Extract nested entity IRIs from a session/DB snapshot dict."""
    if snapshot is None:
        return set()
    iris: set[str] = set()
    for field_name, nmap in mapper_cls.nested_maps.items():
        nested_raw = snapshot.get(field_name)
        if not isinstance(nested_raw, dict):
            continue
        iri = _nested_iri_from_snapshot_item(nested_raw, nmap.nested_mapper, registry)
        if iri is not None:
            iris.add(iri)
    for field_name, cmap in mapper_cls.collection_maps.items():
        raw_items = snapshot.get(field_name)
        if not isinstance(raw_items, list):
            continue
        for item_raw in raw_items:
            if isinstance(item_raw, dict):
                iri = _nested_iri_from_snapshot_item(item_raw, cmap.nested_mapper, registry)
                if iri is not None:
                    iris.add(iri)
    return iris


def nested_iris_from_instance(
    instance: OntoModel,
    mapper_cls: type[Any],
    registry: PrefixRegistry,
) -> set[str]:
    """Extract nested entity IRIs from a live instance."""
    iris: set[str] = set()
    for field_name in mapper_cls.nested_maps:
        nested_value = getattr(instance, field_name, None)
        if nested_value is not None:
            iris.add(build_instance_iri(nested_value, registry))
    for field_name in mapper_cls.collection_maps:
        for item in getattr(instance, field_name, None) or []:
            iris.add(build_instance_iri(item, registry))
    return iris


def _nested_iri_referenced_elsewhere(
    target: Store,
    nested_iri: str,
    *,
    root_iri: str,
    mapper_cls: type[Any],
    registry: PrefixRegistry,
) -> bool:
    """True when another subject in the graph still links to nested_iri."""
    nested_node = NamedNode(nested_iri)
    entity_type = mapper_cls.entity
    link_fields = list(mapper_cls.nested_maps.keys()) + list(mapper_cls.collection_maps.keys())
    for field_name in link_fields:
        pred = predicate_iri(entity_type, field_name, registry)
        if pred is None:
            continue
        pred_node = NamedNode(pred)
        for triple in target:
            if (
                triple[1] == pred_node
                and triple[2] == nested_node
                and term_str(triple[0]) != root_iri
            ):
                return True
    return False


def _remove_stale_nested_subjects(
    target: Store,
    *,
    root_iri: str,
    prior_nested_iris: set[str],
    current_nested_iris: set[str],
    mapper_cls: type[Any],
    registry: PrefixRegistry,
) -> None:
    stale = prior_nested_iris - current_nested_iris
    for nested_iri in stale:
        if _nested_iri_referenced_elsewhere(
            target,
            nested_iri,
            root_iri=root_iri,
            mapper_cls=mapper_cls,
            registry=registry,
        ):
            continue
        _remove_all_subject_triples(target, nested_iri)


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
    prior_nested_iris: set[str] | None = None,
) -> Store:
    """Write a semantic instance subgraph into target using sync semantics."""
    reg = _resolve_registry(instance, registry)
    if mapper_cls is None:
        raise ValueError("sync_instance_to_store() requires mapper_cls=")

    new_graph = instance_to_graph(instance, registry=reg)
    subjects = _subjects_in_graph(new_graph)
    root_iri = build_instance_iri(instance, reg)
    nested_subjects = subjects - {root_iri}
    current_nested_iris = nested_iris_from_instance(instance, mapper_cls, reg)
    prior = prior_nested_iris if prior_nested_iris is not None else set()

    if mode == "add":
        _add_graph_triples(target, new_graph)
        return target

    if mode in ("replace", "patch"):
        _remove_stale_nested_subjects(
            target,
            root_iri=root_iri,
            prior_nested_iris=prior,
            current_nested_iris=current_nested_iris,
            mapper_cls=mapper_cls,
            registry=reg,
        )

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
    snapshot: dict[str, Any] | None = None,
) -> Store:
    """Remove root subject triples and exclusive nested subjects."""
    reg = _resolve_registry(instance, registry)
    if mapper_cls is None:
        raise ValueError("remove_instance_from_store() requires mapper_cls=")

    root_iri = build_instance_iri(instance, reg)
    nested_iris = nested_iris_from_instance(instance, mapper_cls, reg)
    if snapshot is not None:
        nested_iris |= nested_iris_from_snapshot(instance, mapper_cls, snapshot, reg)
    _remove_all_subject_triples(target, root_iri)
    for nested_iri in nested_iris:
        if _nested_iri_referenced_elsewhere(
            target,
            nested_iri,
            root_iri=root_iri,
            mapper_cls=mapper_cls,
            registry=reg,
        ):
            continue
        _remove_all_subject_triples(target, nested_iri)
    return target
