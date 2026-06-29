"""Tests for batch RDF export."""

from __future__ import annotations

from unittest.mock import MagicMock

from ontosql.export import instances_to_graph, instances_to_rdf
from ontosql.sync.materialize import materialize_find
from tests.models import Person


def test_instances_to_graph_single_store(monkeypatch) -> None:
    store_instances: list[object] = []
    original_store = __import__("triplemodel", fromlist=["Store"]).Store

    class TrackingStore(original_store):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            store_instances.append(self)

    monkeypatch.setattr("ontosql.export.instance.Store", TrackingStore)

    people = [Person(id=i, name=f"Person {i}", employer=None) for i in range(100)]
    graph = instances_to_graph(people)
    assert len(store_instances) == 1
    assert len(graph) > 0


def test_instances_to_graph_1k_triples() -> None:
    people = [Person(id=i, name=f"Person {i}", employer=None) for i in range(1000)]
    graph = instances_to_graph(people)
    assert len(graph) >= 1000


def test_instances_to_rdf_batch() -> None:
    people = [Person(id=1, name="Ada", employer=None), Person(id=2, name="Grace", employer=None)]
    body = instances_to_rdf(people, format="turtle")
    assert "Ada" in body and "Grace" in body


def test_materialize_find_uses_batch_export(monkeypatch) -> None:
    calls: list[str] = []

    def track(instances: list[Person], **kwargs: object) -> MagicMock:
        calls.append("batch")
        graph = MagicMock()
        graph.__len__ = lambda self: len(instances)
        return graph

    monkeypatch.setattr("ontosql.sync.materialize.instances_to_graph", track)
    session = MagicMock()
    session.find.return_value = [Person(id=1, name="Ada", employer=None)]
    graph = materialize_find(session, Person)
    assert calls == ["batch"]
    assert len(graph) == 1
