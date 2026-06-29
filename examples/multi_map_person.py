"""Demo: one physical table, schema:Person and foaf:Person semantic views."""

from __future__ import annotations

import _bootstrap  # noqa: F401
from sqlmodel import Field, SQLModel, create_engine

from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property


class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
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
    type_iri = "foaf:Person"
    iri_template = "https://data.example.org/foaf/{id}"

    id: int
    label: str = onto_property("foaf:name")


class SchemaPersonMap(OntoMapper[SchemaPerson]):
    entity = SchemaPerson
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")
    email = Map(PersonRow.email, property="schema:email")


class FoafPersonMap(OntoMapper[FoafPerson]):
    entity = FoafPerson
    id = Map(PersonRow.id)
    label = Map(PersonRow.name, field="label", property="foaf:name")


def main() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    from sqlmodel import Session

    with Session(engine) as raw:
        raw.add(PersonRow(id=1, name="Ada Lovelace", email="ada@example.org"))
        raw.commit()

    with OntoSession(engine, maps=[SchemaPersonMap, FoafPersonMap]) as session:
        schema = session.get(SchemaPerson, id=1)
        foaf = session.get(FoafPerson, id=1)
        assert schema is not None and foaf is not None
        print(f"schema: {schema.name} ({schema.email})")
        print(f"foaf: {foaf.label}")
        print(schema.to_rdf(format="turtle")[:200], "...")


if __name__ == "__main__":
    main()
