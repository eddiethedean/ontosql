# OntoSQL

**Semantic data access for SQL** — map ontology-shaped models onto real database schemas and write CRUD in Python, not RDF.

Real databases are not one table per ontology class. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with an explicit **mapper**. Application code uses semantic types; OntoSQL compiles SQL on the backend. RDF export uses [TripleModel](https://github.com/eddiethedean/triplemodel); graph-native apps can pair OntoSQL with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) — see [Ecosystem](docs/ECOSYSTEM.md).

```bash
pip install ontosql
pip install "ontosql[fastapi]"   # optional API helpers
pip install "ontosql[sparql]"    # optional SparqlModel for graph sync / hybrid apps
```

## Quick start

### 1. Physical models (database truth)

```python
from sqlmodel import Field, SQLModel


class OrgRow(SQLModel, table=True):
    __tablename__ = "orgs"
    id: int | None = Field(default=None, primary_key=True)
    name: str


class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    org_id: int | None = Field(default=None, foreign_key="orgs.id")
```

### 2. Semantic models (what your app uses)

```python
from ontosql import OntoModel, onto_property


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
```

### 3. Maps (explicit SQL bindings)

```python
from ontosql import Map, OntoMapper


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
        join=(PersonRow.org_id == OrgRow.id),
        target=OrgRow,
        nested_map=OrganizationMap,
        property="schema:worksFor",
    )
```

### 4. Session (read path)

```python
from ontosql import OntoSession

with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    ada = session.get(Person, id=1)
    team = session.find(Person, where=Person.name.startswith("A"), limit=20)
```

Async sessions use `AsyncOntoSession` with the same API (`async with`, `await session.get`, `await session.find`).

### 5. Export

```python
print(ada.to_rdf(format="turtle"))
print(ada.to_jsonld())
```

Export walks `OntoModel` + `onto_property` metadata and serializes via **TripleModel** (pyoxigraph). Nested semantic objects become linked RDF resources.

## Features

- **OntoModel** + **onto_property** — semantic entities with ontology IRIs
- **OntoMapper** / **Map** — declarative bindings to columns, joins, and nested entities
- **OntoSession** / **AsyncOntoSession** — `get`, `find`, and `execute_sql` compiled to SQL
- **Semantic queries** — filter on mapped fields (`Person.name.startswith("A")`, etc.)
- **PrefixRegistry** — CURIE expansion and JSON-LD `@context` (CURIE expand via TripleModel)
- **Export** — `to_jsonld()` / `to_rdf()` on semantic instances (TripleModel serializers)
- **FastAPI** (`ontosql[fastapi]`) — content negotiation for JSON-LD and RDF payloads
- **Ecosystem** — [TripleModel](https://github.com/eddiethedean/triplemodel) (core RDF), [SparqlModel](https://github.com/eddiethedean/sparqlmodel) (optional `ontosql[sparql]`)

## FastAPI

```python
from fastapi import FastAPI, Depends, Request
from ontosql import OntoSession
from ontosql.fastapi import negotiate_onto_response

app = FastAPI()

@app.get("/person/{person_id}")
def get_person(person_id: int, request: Request, session: OntoSession = Depends(...)):
    person = session.get(Person, id=person_id)
    return negotiate_onto_response(request, person)
```

See [examples/person_org_demo.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_demo.py) for a minimal read demo.

## Documentation

- [Architecture](https://github.com/eddiethedean/ontosql/blob/main/docs/ARCHITECTURE.md)
- [Ecosystem](https://github.com/eddiethedean/ontosql/blob/main/docs/ECOSYSTEM.md) — OntoSQL, TripleModel, SparqlModel
- [Technical specification](https://github.com/eddiethedean/ontosql/blob/main/docs/SPECS.md)
- [Roadmap](https://github.com/eddiethedean/ontosql/blob/main/docs/ROADMAP.md)
- [Project plan](https://github.com/eddiethedean/ontosql/blob/main/docs/PLAN.md)
- [Dependency assessment](https://github.com/eddiethedean/ontosql/blob/main/docs/DEPS.md)
- [Changelog](https://github.com/eddiethedean/ontosql/blob/main/CHANGELOG.md)

## Development

See [Releasing](https://github.com/eddiethedean/ontosql/blob/main/docs/RELEASING.md) for the version publish checklist.

```bash
pip install -e ".[dev]"
ruff check src tests
ruff format src tests
ty check
pytest --cov=ontosql --cov-fail-under=100
```

## License

MIT — see [LICENSE](https://github.com/eddiethedean/ontosql/blob/main/LICENSE).
