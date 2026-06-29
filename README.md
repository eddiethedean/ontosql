# OntoSQL

**Semantic data access for SQL** — map ontology-shaped models onto real database schemas and write CRUD in Python, not RDF.

Real databases are not one table per ontology class. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with an explicit **mapper**. Application code uses semantic types; OntoSQL compiles SQL on the backend. RDF export uses [TripleModel](https://github.com/eddiethedean/triplemodel); graph-native apps can pair OntoSQL with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) — see [Ecosystem](docs/ECOSYSTEM.md).

**Requirements:** Python 3.10+. See [Compatibility](docs/COMPATIBILITY.md).

> **Production note:** `OntoRouter` (`ontosql[fastapi]`) is **demo-grade** — no authentication, authorization, or rate limiting. Graph sync is **eventually consistent** after SQL commit. See [Security](docs/SECURITY.md) and [Hybrid deployments](docs/HYBRID.md).

## Install

```bash
pip install ontosql
pip install "ontosql[fastapi]"   # OntoRouter + content negotiation
pip install "ontosql[jsonld]"    # optional JSON-LD compact/frame (PyLD)
pip install "ontosql[sparql]"    # SparqlModel graph sync adapter
pip install "ontosql[shacl]"     # SHACL shape generation + validation
```

For async SQLite examples: `pip install aiosqlite greenlet`.

## Start here

1. **Quick start** (below) — models, maps, session CRUD in ~10 minutes
2. [Architecture](docs/ARCHITECTURE.md) — why two model layers and explicit maps
3. [Hybrid deployments](docs/HYBRID.md) — SQL + RDF graph sync (optional)
4. [Technical specification](docs/SPECS.md) — full API reference
5. [FAQ](docs/FAQ.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

Runnable examples (after `pip install ontosql`):

```bash
python examples/person_org_demo.py          # sync CRUD
python examples/person_org_async.py         # async session (needs aiosqlite)
python examples/hybrid_person_org.py        # graph sync + import + SHACL
python examples/multi_map_person.py         # schema:Person vs foaf:Person views
pip install "ontosql[fastapi]" uvicorn && python examples/person_org_api.py
```

## Quick start

### 0. Database engine

```python
from sqlmodel import Session, SQLModel, create_engine

from ontosql import OntoSession

engine = create_engine("sqlite:///./app.db")
SQLModel.metadata.create_all(engine)  # use Alembic in production

# Optional: seed data
with Session(engine) as raw:
  ...
```

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
        fk_column=PersonRow.org_id,
    )
```

See [Cascade policies](docs/guides/cascade-policies.md) for nested write behavior (`link`, `upsert`, `replace`, `ignore`).

### 4. Session (CRUD)

```python
from ontosql import OntoSession, paginate

with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    ada = session.get(Person, id=1)
    team = session.find(Person, where=Person.employer.name.startswith("Analytical"))
    page = paginate(session, Person, limit=20, offset=0)

    new_person = session.save(Person.model_construct(name="Grace Hopper", id=None))
    new_person.name = "Grace M. Hopper"
    session.save(new_person)
    session.delete(new_person)
```

Async sessions use `AsyncOntoSession` with the same API — see [Async guide](docs/getting-started/async.md) and [examples/person_org_async.py](examples/person_org_async.py).

### 5. Export and import

```python
print(ada.to_rdf(format="turtle"))
print(ada.to_jsonld())

from ontosql.import_ import import_from_jsonld  # trailing underscore (import is reserved)

restored = import_from_jsonld(ada.to_jsonld(), PersonMap)
```

Export walks `OntoModel` + `onto_property` metadata and serializes via **TripleModel**. Nested semantic objects become linked RDF resources.

## Features

- **OntoModel** + **onto_property** — semantic entities with ontology IRIs
- **OntoMapper** / **Map** — declarative bindings to columns, joins, and nested entities
- **OntoSession** / **AsyncOntoSession** — `get`, `find`, `save`, `delete`, `paginate`, identity map
- **Semantic queries** — nested paths, `contains` / `endswith`, `OrderBy(desc=True)`
- **CascadePolicy** — explicit nested write behavior on `Map.nested` ([guide](docs/guides/cascade-policies.md))
- **`Map.computed`** — read-only SQL expressions on semantic fields (0.5.0)
- **`Map.collection`** — many-to-many bridge tables with cascade policies (0.5.0)
- **OntoRouter** (`ontosql[fastapi]`) — auto CRUD routes + content negotiation
- **PrefixRegistry** — CURIE expansion and JSON-LD `@context`
- **Export** — `to_jsonld()` / `to_rdf()` on semantic instances
- **Import** — `ontosql.import_` hydrates `OntoModel` from RDF ([FAQ](docs/FAQ.md#import-path))
- **Graph sync** — mirror SQL writes to RDF graphs on commit ([HYBRID.md](docs/HYBRID.md))
- **SHACL** — generate and validate shapes from maps (`ontosql[shacl]`)
- **Prefix bundles** — `PrefixRegistry.curated()` for schema.org / DC Terms

## FastAPI

```python
from fastapi import FastAPI
from ontosql.fastapi import OntoRouter, onto_session_lifespan

app = FastAPI()
onto_session_lifespan(app, engine, [PersonMap, OrganizationMap])
router = OntoRouter(maps=[PersonMap, OrganizationMap])
router.register(Person)
router.include_in(app)
```

See [examples/person_org_api.py](examples/person_org_api.py) for a runnable API.

> **Production warning:** `OntoRouter` is for **development and demos only**. POST/PATCH bodies are validated with generated Pydantic models, but there is **no authentication, authorization, or rate limiting**. Use `AsyncOntoSession` for async apps. See [Security](docs/SECURITY.md) and [SPECS.md](docs/SPECS.md#fastapi-ontosqlfastapi).

## Documentation

### Getting started

- [Installation](docs/getting-started/installation.md)
- [Quick start (standalone)](docs/getting-started/quickstart.md)
- [Async sessions](docs/getting-started/async.md)

### Guides

- [Cascade policies](docs/guides/cascade-policies.md)
- [Bridge tables](docs/guides/bridge-tables.md) — many-to-many `Map.collection`
- [Multi-map views](docs/guides/multi-map-views.md) — one table, multiple semantic entities
- [Postgres dialect](docs/guides/postgres-dialect.md) — UUID, JSONB, ARRAY
- [Hybrid SQL + graph](docs/HYBRID.md)
- [FAQ](docs/FAQ.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Architecture and reference

- [Architecture](docs/ARCHITECTURE.md)
- [Ecosystem](docs/ECOSYSTEM.md) — OntoSQL, TripleModel, SparqlModel
- [Technical specification](docs/SPECS.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Security](docs/SECURITY.md)
- [Dependencies](docs/DEPS.md)

### Project

- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Releasing](docs/RELEASING.md) (maintainers)
- [Documentation site](mkdocs.yml) — build with `mkdocs serve` or `mkdocs build --strict`

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) and [Releasing](docs/RELEASING.md).

```bash
pip install -e ".[dev]"
ruff check src tests
ruff format src tests
ty check
pytest --cov=ontosql --cov-fail-under=90
mkdocs build --strict
```

## License

MIT — see [LICENSE](LICENSE).
