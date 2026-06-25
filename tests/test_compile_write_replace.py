"""Tests for CascadePolicy.REPLACE write compilation."""

from __future__ import annotations

from ontosql import Map, OntoMapper
from ontosql.compile.write import compile_save_plan
from ontosql.mapping.cascade import CascadePolicy
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonRow


def _replace_person_map() -> type[OntoMapper[Person]]:
    class ReplacePersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name, property="schema:name")
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            property="schema:worksFor",
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.REPLACE,
        )

    return ReplacePersonMap


def test_replace_deletes_old_nested_when_fk_changes() -> None:
    mapper = _replace_person_map()
    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=20, name="New Org"),
    )
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    assert len(plan.nested_deletes) == 1
    _, delete_plan = plan.nested_deletes[0]
    assert delete_plan.root.where == {"id": 10}
    assert len(plan.nested) == 1
    _, nested_plan = plan.nested[0]
    assert nested_plan.root.where == {"id": 20}


def test_replace_same_nested_identity_no_delete() -> None:
    mapper = _replace_person_map()
    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=10, name="Renamed Org"),
    )
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    assert plan.nested_deletes == []
    assert len(plan.nested) == 1


def test_replace_clears_and_deletes_when_nested_none() -> None:
    mapper = _replace_person_map()
    person = Person(id=1, name="Ada", employer=None)
    snapshot = {"id": 1, "name": "Ada", "employer": {"id": 10, "name": "Old Org"}}
    plan = compile_save_plan(
        mapper,
        person,
        partial_fields={"employer"},
        is_new=False,
        snapshot=snapshot,
    )
    assert len(plan.nested_deletes) == 1
    assert plan.nested == []
    assert plan.fk_updates == {"org_id": None}


def test_replace_new_instance_no_delete() -> None:
    mapper = _replace_person_map()
    org = Organization.model_construct(id=None, name="Fresh Org")
    person = Person.model_construct(id=1, name="Ada", employer=org)
    plan = compile_save_plan(mapper, person, partial_fields={"employer"}, is_new=True)
    assert plan.nested_deletes == []
    assert len(plan.nested) == 1
