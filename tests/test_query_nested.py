"""Tests for nested field paths and additional filters."""

from __future__ import annotations

from ontosql.query.expr import Contains, EndsWith, FieldPath, OrderBy
from tests.models import Person


def test_nested_field_path() -> None:
    path = Person.employer.name
    assert isinstance(path, FieldPath)
    assert path.parts == ("employer", "name")
    deeper = Person.employer.name.extra  # noqa: SLF001
    assert deeper.parts == ("employer", "name", "extra")


def test_contains_endswith() -> None:
    assert isinstance(Person.name.contains("da"), Contains)
    assert isinstance(Person.name.endswith("ace"), EndsWith)


def test_order_by_desc() -> None:
    ob = OrderBy(Person.name, desc=True)
    assert ob.desc is True


def test_nested_where_compiles(onto_session) -> None:
    rows = onto_session.find(
        Person,
        where=Person.employer.name == "Analytical Engines Inc.",
    )
    assert len(rows) == 2
    assert all(p.employer is not None for p in rows)


def test_contains_and_endswith_find(onto_session) -> None:
    by_contains = onto_session.find(Person, where=Person.name.contains("Lovelace"))
    assert len(by_contains) == 1
    assert by_contains[0].name == "Ada Lovelace"

    by_endswith = onto_session.find(Person, where=Person.name.endswith("Babbage"))
    assert len(by_endswith) == 1


def test_order_by_nested(onto_session) -> None:
    from ontosql.query.expr import OrderBy

    rows = onto_session.find(
        Person,
        order_by=OrderBy(Person.employer.name, desc=True),
        where=Person.employer.name.is_null() | Person.employer.name.startswith("A"),
    )
    assert len(rows) >= 1
