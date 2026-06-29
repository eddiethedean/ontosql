"""Tests for query expression compilation."""

from __future__ import annotations

import pytest
from sqlalchemy import column

from ontosql.query.expr import AndExpr, CompileError, OrExpr, compile_expr
from tests.models import Person


def _compile_sql(clause: object) -> str:
    return str(clause.compile(compile_kwargs={"literal_binds": True}))  # type: ignore[union-attr]


def test_compile_comparison() -> None:
    col = column("name")
    expr = Person.name == "Ada"
    clause = compile_expr(expr, lambda ref: col)
    compiled = _compile_sql(clause)
    assert "name" in compiled
    assert "Ada" in compiled
    assert "=" in compiled


def test_compile_startswith() -> None:
    col = column("name")
    expr = Person.name.startswith("A")
    clause = compile_expr(expr, lambda ref: col)
    assert "LIKE" in str(clause).upper() or "like" in str(clause)


def test_compile_and() -> None:
    col = column("name")
    expr = (Person.name.startswith("A")) & (Person.name == "Ada")
    clause = compile_expr(expr, lambda ref: col)
    compiled = _compile_sql(clause).upper()
    assert "AND" in compiled
    assert "LIKE" in compiled
    assert "ADA" in compiled


def test_compile_bare_field_raises() -> None:
    with pytest.raises(CompileError):
        compile_expr(Person.name, lambda ref: column("x"))


def test_compile_unsupported() -> None:
    with pytest.raises(CompileError):
        compile_expr("not-an-expr", lambda ref: column("x"))


def test_compile_or() -> None:
    col = column("name")
    expr = OrExpr((Person.name.startswith("A"), Person.name == "B"))
    clause = compile_expr(expr, lambda ref: col)
    compiled = _compile_sql(clause).upper()
    assert "OR" in compiled
    assert "LIKE" in compiled
    assert "B" in compiled


def test_compile_empty_and_raises() -> None:
    with pytest.raises(CompileError, match="Empty AND"):
        compile_expr(AndExpr(()), lambda ref: column("name"))


def test_compile_unknown_op_raises() -> None:
    from ontosql.query.expr import Comparison

    cmp = Comparison(Person.name, "bogus", "x")
    with pytest.raises(CompileError, match="Unknown comparison"):
        compile_expr(cmp, lambda ref: column("name"))
