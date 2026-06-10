"""Tests for write compile plans."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ontosql import Map, OntoMapper
from ontosql.compile.write import WriteCompileError, compile_delete_plan, compile_save_plan
from ontosql.mapping.cascade import CascadePolicy
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def test_compile_insert_person() -> None:
    person = Person(id=99, name="Grace Hopper", employer=None)
    plan = compile_save_plan(PersonMap, person, is_new=True)
    assert plan.operation == "insert"
    assert plan.root.values == {"id": 99, "name": "Grace Hopper"}
    assert plan.root.where is None


def test_compile_update_person_partial() -> None:
    person = Person(
        id=1,
        name="Ada L.",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    plan = compile_save_plan(PersonMap, person, partial_fields={"name"})
    assert plan.operation == "update"
    assert plan.root.values == {"name": "Ada L."}
    assert plan.root.where == {"id": 1}


def test_compile_link_sets_fk() -> None:
    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Acme"))
    plan = compile_save_plan(PersonMap, person, partial_fields={"employer"})
    assert plan.fk_updates == {"org_id": 10}
    assert plan.nested == []


def test_compile_link_clears_fk() -> None:
    person = Person(id=1, name="Ada", employer=None)
    plan = compile_save_plan(PersonMap, person, partial_fields={"employer"})
    assert plan.fk_updates == {"org_id": None}


def test_compile_upsert_nested() -> None:
    class UpsertPersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name, property="schema:name")
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            property="schema:worksFor",
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.UPSERT,
        )

    org = Organization(id=20, name="New Org")
    person = Person(id=1, name="Ada", employer=org)
    plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"})
    assert len(plan.nested) == 1
    _, nested_plan = plan.nested[0]
    assert nested_plan.operation == "update"
    assert nested_plan.root.where == {"id": 20}


def test_compile_delete_person() -> None:
    person = Person(id=1, name="Ada", employer=None)
    plan = compile_delete_plan(PersonMap, person)
    assert plan.root.where == {"id": 1}


def test_compile_delete_no_primary_table() -> None:
    bad = MagicMock()
    bad.__name__ = "Bad"
    bad.identity_field = "id"
    bad.column_maps = {"id": PersonMap.column_maps["id"]}
    bad.primary_table = None
    with pytest.raises(WriteCompileError):
        compile_delete_plan(bad, Person(id=1, name="Ada", employer=None))


def test_compile_upsert_nested_partial_fields() -> None:
    class UpsertPersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.UPSERT,
        )

    org = Organization.model_construct(id=25, name="Partial Org")
    person = Person.model_construct(id=1, name="Ada", employer=org)
    plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"}, is_new=False)
    assert plan.nested


def test_compile_upsert_skips_null_employer() -> None:
    class UpsertPersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.UPSERT,
        )

    person = Person(id=1, name="Ada", employer=None)
    plan = compile_save_plan(UpsertPersonMap, person, partial_fields={"employer"})
    assert plan.nested == []


def test_compile_delete_requires_identity() -> None:
    person = Person(id=1, name="Ada", employer=None)
    object.__setattr__(person, "id", None)
    with pytest.raises(WriteCompileError, match="identity"):
        compile_delete_plan(PersonMap, person)


def test_compile_ignore_cascade_skips_nested() -> None:
    from ontosql import Map

    class IgnorePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name)
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.IGNORE,
        )

    person = Person(id=1, name="Ada", employer=Organization(id=10, name="Acme"))
    plan = compile_save_plan(IgnorePersonMap, person)
    assert plan.nested == []
    assert plan.fk_updates == {}
