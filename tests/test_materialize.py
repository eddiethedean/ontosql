"""Tests for graph materialization."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from ontosql.export import instances_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.sync.materialize import materialize_find
from tests.conftest import graph_literal_values, graph_object_iris
from tests.models import Organization, OrganizationMap, Person, PersonMap


@pytest.fixture
def session(sync_engine):
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as s:
        yield s


def test_materialize_single_instance() -> None:
    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=10, name="Acme"),
    )
    graph = instances_to_graph([person])
    reg = PrefixRegistry()
    subject = "https://data.example.org/person/1"
    names = graph_literal_values(graph, subject, "schema:name", registry=reg)
    assert names == ["Ada"]
    org_names = graph_literal_values(
        graph, "https://data.example.org/org/10", "schema:name", registry=reg
    )
    assert org_names == ["Acme"]
    works_for = graph_object_iris(graph, subject, "schema:worksFor", registry=reg)
    assert works_for == ["https://data.example.org/org/10"]


def test_materialize_find(session) -> None:
    graph = materialize_find(session, Person, limit=2)
    reg = PrefixRegistry()
    person_subjects = {
        str(triple[0].value)
        for triple in graph
        if str(triple[1].value) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        and str(triple[2].value) == reg.expand("schema:Person")
    }
    assert len(person_subjects) == 2
    ada_names = graph_literal_values(
        graph, "https://data.example.org/person/1", "schema:name", registry=reg
    )
    assert ada_names == ["Ada Lovelace"]
