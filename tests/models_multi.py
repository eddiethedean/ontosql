"""Multi-map view fixtures — one table, two semantic entities."""

from __future__ import annotations

from sqlmodel import Field, SQLModel

from ontosql import Map, OntoMapper, OntoModel, onto_property


class SharedPersonRow(SQLModel, table=True):
    __tablename__ = "shared_people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str | None = None


class SchemaPerson(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"

    id: int
    name: str = onto_property("schema:name")
    email: str | None = onto_property("schema:email")


class FoafPerson(OntoModel):
    type_iri = "http://xmlns.com/foaf/0.1/Person"
    iri_template = "https://data.example.org/foaf/{id}"

    id: int
    label: str = onto_property("foaf:name", iri="http://xmlns.com/foaf/0.1/name")


class SchemaPersonMap(OntoMapper[SchemaPerson]):
    entity = SchemaPerson
    id = Map(SharedPersonRow.id)
    name = Map(SharedPersonRow.name, property="schema:name")
    email = Map(SharedPersonRow.email, property="schema:email")


class FoafPersonMap(OntoMapper[FoafPerson]):
    entity = FoafPerson
    id = Map(SharedPersonRow.id)
    label = Map(SharedPersonRow.name, field="label", property="foaf:name")
