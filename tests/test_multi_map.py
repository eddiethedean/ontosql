"""Tests for multi-map views over one physical table."""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from ontosql import OntoSession
from tests.models_multi import (
    FoafPerson,
    FoafPersonMap,
    SchemaPerson,
    SchemaPersonMap,
    SharedPersonRow,
)


@pytest.fixture
def multi_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            SharedPersonRow(id=1, name="Ada Lovelace", email="ada@example.org"),
        )
        session.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def multi_session(multi_engine):
    with OntoSession(multi_engine, maps=[SchemaPersonMap, FoafPersonMap]) as session:
        yield session


def test_same_row_two_semantic_views(multi_session) -> None:
    schema = multi_session.get(SchemaPerson, id=1)
    foaf = multi_session.get(FoafPerson, id=1)
    assert schema is not None and foaf is not None
    assert schema.name == "Ada Lovelace"
    assert foaf.label == "Ada Lovelace"
    assert schema.email == "ada@example.org"


def test_write_via_one_map_visible_in_other(multi_session) -> None:
    schema = multi_session.get(SchemaPerson, id=1)
    assert schema is not None
    schema.name = "Ada M. Lovelace"
    multi_session.save(schema)
    foaf = multi_session.get(FoafPerson, id=1)
    assert foaf is not None
    assert foaf.label == "Ada M. Lovelace"


def test_export_different_type_iri(multi_session) -> None:
    schema = multi_session.get(SchemaPerson, id=1)
    foaf = multi_session.get(FoafPerson, id=1)
    assert schema is not None and foaf is not None
    schema_ttl = schema.to_rdf(format="turtle")
    foaf_ttl = foaf.to_rdf(format="turtle")
    assert "schema:Person" in schema_ttl or "https://schema.org/Person" in schema_ttl
    assert "foaf:Person" in foaf_ttl or "http://xmlns.com/foaf/0.1/Person" in foaf_ttl
