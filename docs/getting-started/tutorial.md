# Tutorial: Person and Organization CRUD

End-to-end walkthrough from install to semantic queries. Works after `pip install ontosql` only — no repository clone.

**Time:** 15–20 minutes. **Prerequisite:** [Installation](installation.md) (Python 3.10+, SQLModel familiarity).

## 1. Install

```bash
pip install ontosql
```

## 2. Three layers

OntoSQL uses three artifacts you define once per entity:

| Layer | Type | Role |
|-------|------|------|
| Physical | `SQLModel` with `table=True` | Mirrors database tables |
| Semantic | `OntoModel` | Application entities with ontology metadata |
| Mapping | `OntoMapper` | Explicit field → column/join bindings |

See [Architecture](../ARCHITECTURE.md) for rationale.

## 3. Define models and maps

Save as `tutorial.py`:

```python
from sqlmodel import Field, Session, SQLModel, create_engine

from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property

# --- physical row models ---
class OrgRow(SQLModel, table=True):
    __tablename__ = "orgs"
    id: int | None = Field(default=None, primary_key=True)
    name: str

class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    org_id: int | None = Field(default=None, foreign_key="orgs.id")

# --- semantic entities ---
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

# --- mappers ---
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
```

`type_iri` and `iri_template` enable optional RDF export later; they do not require a graph database.

## 4. Create tables and seed data

```python
engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)

with Session(engine) as raw:
    raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
    raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
    raw.commit()
```

You can also seed with `session.save()` — see [quick start](quickstart.md).

## 5. Read with OntoSession

```python
with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    ada = session.get(Person, identity=1)
    print(ada.name, "→", ada.employer.name if ada.employer else "no employer")
```

Always pass every mapper the session needs: `maps=[PersonMap, OrganizationMap]`.

## 6. Write: create and update

```python
with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    grace = session.save(Person.model_construct(name="Grace Hopper"))
    print("Created id=", grace.id)

    grace.name = "Grace M. Hopper"
    session.save(grace)
```

`save()` on exit commits the transaction. Nested `employer` uses default `link` cascade — the org row must already exist.

## 7. Semantic queries

```python
with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    results = session.find(
        Person,
        where=Person.employer.name.startswith("Analytical"),
    )
    for p in results:
        print(p.name)
```

See [semantic queries](../guides/semantic-queries.md) for filters, ordering, and pagination.

## 8. Optional RDF export

Inside the same session block:

```python
    print(ada.to_jsonld())
    print(ada.to_rdf(format="turtle")[:200])
```

Or use module-level I/O: `from ontosql import to_jsonld`.

## 9. Run

```bash
python tutorial.py
```

## Read next

| Goal | Next step |
|------|-----------|
| Async sessions | [Async sessions](async.md) |
| FastAPI API | [FastAPI quick start](../guides/fastapi-quickstart.md) |
| Nested write policies | [Cascade policies](../guides/cascade-policies.md) |
| Hybrid SQL + RDF | [HYBRID.md](../HYBRID.md) |
| Full API contract | [SPECS.md](../SPECS.md) |
