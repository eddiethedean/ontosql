"""Tests for row hydration."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ontosql.compile.plan import SelectPlan
from ontosql.compile.select import compile_select_plan
from ontosql.session.hydrate import _row_get, hydrate_first, hydrate_row
from tests.models import PersonMap


def test_hydrate_row_nested_employer() -> None:
    plan = compile_select_plan(PersonMap, id_value=1)
    row = {
        "people_id": 1,
        "people_name": "Ada Lovelace",
        "employer_orgs_id": 10,
        "employer_orgs_name": "Analytical Engines Inc.",
    }
    person = hydrate_row(plan, row)
    assert person.name == "Ada Lovelace"
    assert person.employer is not None
    assert person.employer.name == "Analytical Engines Inc."


def test_hydrate_nested_null_identity() -> None:
    plan = compile_select_plan(PersonMap, id_value=3)
    row = {
        "people_id": 3,
        "people_name": "Solo",
        "employer_orgs_id": None,
        "employer_orgs_name": "Ghost",
    }
    person = hydrate_row(plan, row)
    assert person.employer is None


def test_hydrate_first_empty() -> None:
    plan = compile_select_plan(PersonMap, id_value=999)

    class EmptyResult:
        def first(self):
            return None

    assert hydrate_first(plan, EmptyResult()) is None


def test_hydrate_raises_without_mapper() -> None:
    plan = SelectPlan(select=MagicMock(), mapper_cls=None)
    with pytest.raises(ValueError, match="no mapper_cls"):
        hydrate_row(plan, {})


def test_row_get_attr() -> None:
    class Row:
        people_id = 1

    assert _row_get(Row(), "people_id") == 1
