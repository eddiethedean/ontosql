"""Fixtures for computed field mapping tests."""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Field, SQLModel

from ontosql import Map, OntoMapper, OntoModel, onto_property


class NamedPersonRow(SQLModel, table=True):
    __tablename__ = "named_people"
    id: int | None = Field(default=None, primary_key=True)
    first_name: str
    last_name: str


class NamedPerson(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"

    id: int
    first_name: str = onto_property("schema:givenName")
    last_name: str = onto_property("schema:familyName")
    display_name: str = onto_property("schema:name")


class NamedPersonMap(OntoMapper[NamedPerson]):
    entity = NamedPerson
    id = Map(NamedPersonRow.id)
    first_name = Map(NamedPersonRow.first_name, property="schema:givenName")
    last_name = Map(NamedPersonRow.last_name, property="schema:familyName")
    display_name = Map.computed(
        func.trim(NamedPersonRow.first_name) + " " + func.trim(NamedPersonRow.last_name),
        field="display_name",
        property="schema:name",
    )
