"""Tests for select-plan skeleton caching."""

from __future__ import annotations

from ontosql.compile.cache import select_skeleton
from ontosql.compile.select import compile_select_plan
from tests.models import Person, PersonMap


def test_select_skeleton_cached() -> None:
    sk1 = select_skeleton(PersonMap)
    sk2 = select_skeleton(PersonMap)
    assert sk1 is sk2


def test_compile_select_same_from_clause() -> None:
    plan1 = compile_select_plan(PersonMap, limit=10)
    plan2 = compile_select_plan(PersonMap, where=Person.name == "Ada Lovelace")
    assert str(plan1.select.froms) == str(plan2.select.froms)


def test_compile_select_different_where() -> None:
    plan_all = compile_select_plan(PersonMap)
    plan_filtered = compile_select_plan(PersonMap, where=Person.name == "Ada Lovelace")
    assert str(plan_all.select.whereclause) != str(plan_filtered.select.whereclause)
