"""Tests for batch RDF export."""

from __future__ import annotations

from ontosql.export import instances_to_graph, instances_to_jsonld, instances_to_rdf
from tests.conftest import graph_literal_values
from tests.models import Organization, Person


def test_instances_to_graph_empty() -> None:
    graph = instances_to_graph([])
    assert len(graph) == 0


def test_instances_to_graph_single_store() -> None:
    from triplemodel import Store

    store_instances: list[Store] = []

    class TrackingStore(Store):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            store_instances.append(self)

    import ontosql.export.instance as instance_mod

    original = instance_mod.Store
    instance_mod.Store = TrackingStore
    try:
        people = [Person(id=i, name=f"Person {i}", employer=None) for i in range(100)]
        graph = instances_to_graph(people)
        assert len(store_instances) == 1
        assert len(graph) > 0
    finally:
        instance_mod.Store = original


def test_instances_to_graph_1k_triples() -> None:
    people = [Person(id=i, name=f"Person {i}", employer=None) for i in range(1000)]
    graph = instances_to_graph(people)
    assert len(graph) >= 1000
    all_literals = {str(getattr(t[2], "value", t[2])) for t in graph if hasattr(t[2], "value")}
    assert "Person 0" in all_literals
    assert "Person 999" in all_literals


def test_instances_to_graph_deduplicates_shared_nested() -> None:
    org = Organization(id=10, name="Shared Org")
    people = [
        Person(id=1, name="Ada", employer=org),
        Person(id=2, name="Grace", employer=org),
    ]
    graph = instances_to_graph(people)
    org_names = graph_literal_values(graph, "https://data.example.org/org/10", "schema:name")
    assert org_names == ["Shared Org"]


def test_instances_to_jsonld_batch() -> None:
    people = [
        Person(id=1, name="Ada", employer=None),
        Person(id=2, name="Grace", employer=None),
    ]
    doc = instances_to_jsonld(people)
    assert "@context" in doc
    graph = doc.get("@graph", doc)
    if isinstance(graph, dict):
        graph = [graph]
    names = []
    for node in graph:
        if not isinstance(node, dict):
            continue
        name_field = node.get("https://schema.org/name") or node.get("schema:name")
        if isinstance(name_field, list) and name_field:
            names.append(name_field[0].get("@value", name_field[0]))
        elif isinstance(name_field, str):
            names.append(name_field)
    assert "Ada" in names
    assert "Grace" in names


def test_instances_to_rdf_batch() -> None:
    people = [Person(id=1, name="Ada", employer=None), Person(id=2, name="Grace", employer=None)]
    body = instances_to_rdf(people, format="turtle")
    assert "Ada" in body and "Grace" in body
