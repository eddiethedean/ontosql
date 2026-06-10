"""Tests for SELECT compilation."""

from __future__ import annotations

import pytest

from ontosql.compile.select import (
    _column_for_field,
    compile_count_statement,
    compile_select_plan,
)
from ontosql.query.expr import FieldPath, FieldRef
from tests.models import Person, PersonMap


def test_compile_find_includes_join() -> None:
    plan = compile_select_plan(PersonMap, where=Person.name.startswith("A"))
    sql = str(plan.select.compile(compile_kwargs={"literal_binds": True}))
    assert "people" in sql.lower()
    assert "orgs" in sql.lower()
    assert "join" in sql.lower() or "LEFT OUTER JOIN" in sql.upper()


def test_compile_get_by_id() -> None:
    plan = compile_select_plan(PersonMap, id_value=1)
    sql = str(plan.select.compile(compile_kwargs={"literal_binds": True}))
    assert "1" in sql


def test_compile_get_by_iri_invalid() -> None:
    with pytest.raises(ValueError, match="Cannot parse IRI"):
        compile_select_plan(PersonMap, iri="not-a-valid-iri")


def test_compile_order_by() -> None:
    plan = compile_select_plan(PersonMap, order_by=Person.name)
    sql = str(plan.select.compile(compile_kwargs={"literal_binds": True}))
    assert "ORDER BY" in sql.upper()


def test_compile_count() -> None:
    stmt = compile_count_statement(PersonMap, where=Person.name.startswith("A"))
    assert "count" in str(stmt).lower()


def test_plan_label_for() -> None:
    plan = compile_select_plan(PersonMap)
    assert plan.label_for("id") == "people_id"
    assert plan.label_for("id", nested="employer") == "employer_orgs_id"
    with pytest.raises(KeyError):
        plan.label_for("missing")


def test_column_for_field_errors() -> None:
    with pytest.raises(KeyError):
        _column_for_field(PersonMap, FieldPath(Person, ("missing",)))
    with pytest.raises(KeyError):
        _column_for_field(PersonMap, FieldRef(Person, "missing"))
    col = _column_for_field(PersonMap, FieldPath(Person, ("name",)))
    assert col is not None
