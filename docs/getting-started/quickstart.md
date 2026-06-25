# Quick start

This guide is **self-contained** — it works after `pip install ontosql` only (no repo clone required).

## 1. Install

```bash
pip install ontosql
```

## 2. Copy the example models

Save as `demo.py` or run from the repository:

```bash
pip install ontosql
python examples/person_org_demo.py
```

The [examples/models.py](https://github.com/eddiethedean/ontosql/blob/main/examples/models.py) module defines physical tables, semantic models, and mappers for Person / Organization.

## 3. Minimal script

```python
from sqlmodel import Field, Session, SQLModel, create_engine

from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property

# --- physical ---
class OrgRow(SQLModel, table=True):
    __tablename__ = "orgs"
    id: int | None = Field(default=None, primary_key=True)
    name: str

class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    org_id: int | None = Field(default=None, foreign_key="orgs.id")

# --- semantic ---
class Organization(OntoModel):
    type_iri = "schema:Organization"
    iri_template = "https://data.example.org/org/{id}"
    id: int
    name: str = onto_property("schema:name")

class Person(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"
    id: int
    name: str = onto_property("schema:name")
    employer: Organization | None = onto_property("schema:worksFor")

# --- maps ---
class OrganizationMap(OntoMapper[Organization]):
    entity = Organization
    id = Map(OrgRow.id)
    name = Map(OrgRow.name, property="schema:name")

class PersonMap(OntoMapper[Person]):
    entity = Person
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")
    employer = Map.nested(
        Organization,
        join=PersonRow.org_id == OrgRow.id,
        nested_map=OrganizationMap,
        property="schema:worksFor",
        fk_column=PersonRow.org_id,
    )

# --- run ---
engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
with Session(engine) as raw:
    raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
    raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
    raw.commit()

with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    ada = session.get(Person, id=1)
    print(ada.name, ada.employer.name if ada.employer else "")
    print(ada.to_rdf(format="turtle")[:200])
```

## 4. Read next

- [Architecture](../ARCHITECTURE.md) — design rationale
- [Cascade policies](../guides/cascade-policies.md) — nested writes
- [HYBRID.md](../HYBRID.md) — graph sync (optional)
- [SPECS.md](../SPECS.md) — full API
