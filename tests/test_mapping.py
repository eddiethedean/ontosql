"""Tests for OntoMapper and Map."""

from __future__ import annotations

import pytest
from sqlmodel import Field, SQLModel

from ontosql import OntoMapper, OntoModel
from ontosql.mapping.registry import MapperRegistry
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


def test_mapper_bindings() -> None:
    assert "id" in PersonMap.column_maps
    assert "employer" in PersonMap.nested_maps
    assert PersonMap.entity is Person


def test_mapper_registry() -> None:
    reg = MapperRegistry()
    reg.register_many([PersonMap, OrganizationMap])
    assert reg.get(Person) is PersonMap
    assert reg.get(Organization) is OrganizationMap


def test_duplicate_mapper_raises() -> None:
    reg = MapperRegistry()
    reg.register(PersonMap)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(PersonMap)


def test_mapper_fk_column_required() -> None:
    from ontosql import Map

    class E(Person):
        pass

    with pytest.raises(ValueError, match="fk_column"):

        class BadMap(OntoMapper[E]):
            entity = E
            id = Map(PersonRow.id)
            employer = Map.nested(
                Organization,
                join=PersonRow.org_id == OrgRow.id,
                nested_map=OrganizationMap,
            )


def test_mapper_for_entity_and_identity() -> None:
    from ontosql.mapping.mapper import OntoMapper

    reg = MapperRegistry()
    reg.register_many([PersonMap, OrganizationMap])
    assert OntoMapper.for_entity(Person, registry=reg) is PersonMap
    assert PersonMap.identity_column() is not None


def test_nested_map_target_table() -> None:
    nmap = PersonMap.nested_maps["employer"]
    assert nmap.target_table is OrganizationMap.primary_table


def test_mapper_requires_column_map() -> None:
    class EmptyRow(SQLModel, table=True):
        __tablename__ = "empty"
        id: int | None = Field(default=None, primary_key=True)

    class EmptyEntity(OntoModel):
        id: int

    with pytest.raises(ValueError, match="requires at least one column map"):

        class BadMap(OntoMapper[EmptyEntity]):
            entity = EmptyEntity  # noqa: F841 — no Map bindings
