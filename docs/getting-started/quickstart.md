# Quick start

Three tiers — stop when you have what you need. **Tier 1 works after `pip install ontosql` only** (no repo clone).

## Tier 1: SQL CRUD (no RDF required)

### 1. Install

```bash
pip install ontosql
```

### 2. Minimal script

Save as `demo.py` and run `python demo.py`:

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
    ada = session.get(Person, identity=1)
    print(ada.name, ada.employer.name if ada.employer else "")
```

`type_iri` and `iri_template` enable RDF export later; they do not require a graph database.

## Tier 2: RDF export (optional)

Add to the end of your script:

```python
    print(ada.to_rdf(format="turtle")[:200])
    print(ada.to_jsonld())
```

## Tier 3: Graph sync (optional)

Mirror SQL writes to an in-memory RDF graph on commit. See [HYBRID.md](../HYBRID.md) and [examples/hybrid_person_org.py](https://github.com/eddiethedean/ontosql/blob/main/examples/hybrid_person_org.py) (requires a repository clone).

## Examples from a clone

The `examples/` directory is **not** in the PyPI wheel. After cloning:

```bash
git clone https://github.com/eddiethedean/ontosql.git
cd ontosql && pip install -e ".[dev]"
python examples/person_org_demo.py
```

Shared models live in [examples/models.py](https://github.com/eddiethedean/ontosql/blob/main/examples/models.py).

## Read next

- [Architecture](../ARCHITECTURE.md) — design rationale
- [Cascade policies](../guides/cascade-policies.md) — nested writes (`link` vs `replace`)
- [Ecosystem](../ECOSYSTEM.md) — when to use OntoSQL vs SQLModel vs SparqlModel
- [SPECS.md](../SPECS.md) — full API
