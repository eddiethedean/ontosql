"""Tests for Map.computed read-only fields."""

from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine

from ontosql import OntoSession
from ontosql.compile.write import WriteCompileError
from ontosql.query.expr import OrderBy
from tests.models_computed import NamedPerson, NamedPersonMap, NamedPersonRow


@pytest.fixture
def computed_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(NamedPersonRow(id=1, first_name="Ada", last_name="Lovelace"))
        session.add(NamedPersonRow(id=2, first_name="Grace", last_name="Hopper"))
        session.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def computed_session(computed_engine):
    with OntoSession(computed_engine, maps=[NamedPersonMap]) as session:
        yield session


def test_computed_field_hydrated_on_get(computed_session) -> None:
    person = computed_session.get(NamedPerson, id=1)
    assert person is not None
    assert person.display_name == "Ada Lovelace"


def test_computed_field_filter(computed_session) -> None:
    rows = computed_session.find(NamedPerson, where=NamedPerson.display_name == "Grace Hopper")
    assert len(rows) == 1
    assert rows[0].first_name == "Grace"


def test_computed_field_order_by(computed_session) -> None:
    rows = computed_session.find(
        NamedPerson,
        order_by=OrderBy(NamedPerson.display_name, desc=True),
    )
    assert [p.display_name for p in rows] == ["Grace Hopper", "Ada Lovelace"]


def test_save_ignores_computed_on_insert(computed_session) -> None:
    created = computed_session.save(
        NamedPerson.model_construct(first_name="Alan", last_name="Turing", id=None)
    )
    reloaded = computed_session.get(NamedPerson, id=created.id)
    assert reloaded is not None
    assert reloaded.display_name == "Alan Turing"


def test_save_raises_when_computed_in_partial_update(computed_session) -> None:
    person = computed_session.get(NamedPerson, id=1)
    assert person is not None
    person.display_name = "Changed"
    with pytest.raises(WriteCompileError, match="computed fields"):
        computed_session.save(person)


def test_mapper_duplicate_field_raises() -> None:
    from ontosql import Map, OntoMapper

    with pytest.raises(ValueError, match="duplicate semantic field names"):

        class BadMap(OntoMapper[NamedPerson]):
            entity = NamedPerson
            id = Map(NamedPersonRow.id)
            first_name = Map(NamedPersonRow.first_name)
            display_name = Map.computed(
                NamedPersonRow.first_name,
                field="first_name",
            )
