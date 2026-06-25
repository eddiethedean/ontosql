"""Integration tests for SparqlModel graph sync."""

from __future__ import annotations

import pytest

pytest.importorskip("sparqlmodel")

from pyoxigraph import NamedNode
from sparqlmodel import SPARQLSession
from triplemodel import RDF_TYPE

from ontosql import OntoSession
from ontosql.registry import PrefixRegistry
from ontosql.sync.sparql import OntoGraphSync
from tests.models import Organization, OrganizationMap, Person, PersonMap


@pytest.fixture
def hybrid_setup(sync_engine):
    _ = sync_engine
    graph_session = SPARQLSession()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=graph_session._store,
        graph_sync_mode="replace",
    ) as sql_session:
        yield sql_session, graph_session


def test_save_pushes_to_sparql_session(sync_engine) -> None:
    graph_session = SPARQLSession()
    with OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=graph_session._store,
        graph_sync_mode="replace",
    ) as sql_session:
        person = Person(
            id=60,
            name="Graph Sync Person",
            employer=Organization(id=10, name="Analytical Engines Inc."),
        )
        saved = sql_session.save(person)
    sync = OntoGraphSync(graph_session, maps=[PersonMap, OrganizationMap])
    iri = sync.instance_iri(saved)
    reg = PrefixRegistry()
    subject = NamedNode(iri)
    types = list(graph_session._store.graph.objects(subject, NamedNode(RDF_TYPE)))
    assert NamedNode(reg.expand("schema:Person")) in types


def test_onto_graph_sync_push_pull(sync_engine) -> None:
    graph_session = SPARQLSession()
    sync = OntoGraphSync(graph_session, maps=[PersonMap, OrganizationMap])
    person = Person(
        id=70,
        name="Push Pull",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    sync.push(person)
    iri = sync.instance_iri(person)
    pulled = sync.pull(Person, iri=iri)
    assert pulled is not None
    assert pulled.id == 70
    assert pulled.name == "Push Pull"
    assert pulled.employer is not None
    assert pulled.employer.id == 10
