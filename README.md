# OntoSQL

[![PyPI version](https://img.shields.io/pypi/v/ontosql)](https://pypi.org/project/ontosql/)
[![CI](https://github.com/eddiethedean/ontosql/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ontosql/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/ontosql)](https://pypi.org/project/ontosql/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Documentation](https://readthedocs.org/projects/ontosql/badge/?version=latest)](https://ontosql.readthedocs.io/en/latest/)

**Semantic data access for SQL** — a Python mapper (SQLModel + Pydantic) with optional RDF export. **Not** a SPARQL database or OBDA query engine.

> **Who is this for?** Teams building **SQL-first** apps (Postgres, SQLite) that want **ontology-shaped Python models** and optional JSON-LD/RDF APIs. RDF and graph sync are optional — you can use OntoSQL for semantic CRUD only.

Real databases are not one table per ontology class. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with an explicit **mapper**. Application code uses semantic types; OntoSQL compiles SQL on the backend. Optional RDF export uses [TripleModel](https://github.com/eddiethedean/triplemodel); graph-native apps can pair OntoSQL with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) — see [Ecosystem](https://ontosql.readthedocs.io/en/latest/ECOSYSTEM.html).

**Requirements:** Python 3.10+. See [Compatibility](https://ontosql.readthedocs.io/en/latest/COMPATIBILITY.html).

> **Production note:** `OntoRouter` requires **`dependencies=[Depends(your_auth)]`** before internet exposure. Defaults: async sessions, semantic validation, 64 KiB body cap. Graph sync is **eventually consistent** after SQL commit. See [Security](https://ontosql.readthedocs.io/en/latest/SECURITY.html).

## Install

```bash
pip install ontosql
pip install "ontosql[async]"     # AsyncOntoSession + SQLite (aiosqlite, greenlet)
pip install "ontosql[fastapi]"   # OntoRouter + content negotiation
pip install "ontosql[jsonld]"    # optional JSON-LD compact/frame (PyLD)
pip install "ontosql[sparql]"    # SparqlModel graph sync adapter
pip install "ontosql[shacl]"     # SHACL shape generation + validation
# Combine extras: pip install "ontosql[fastapi,shacl,async]"
```

## Start here

1. **Try it (PyPI)** — copy the [standalone quick start](https://ontosql.readthedocs.io/en/latest/getting-started/quickstart.html#tier-1-sql-crud-no-rdf-required) into `demo.py` (no clone required) · [Start here](https://ontosql.readthedocs.io/en/latest/guides/start-here.html)
2. [Architecture](https://ontosql.readthedocs.io/en/latest/ARCHITECTURE.html) — why two model layers and explicit maps
3. [Hybrid deployments](https://ontosql.readthedocs.io/en/latest/HYBRID.html) — SQL + RDF graph sync (optional)
4. [Technical specification](https://ontosql.readthedocs.io/en/latest/SPECS.html) — full API reference
5. [FAQ](https://ontosql.readthedocs.io/en/latest/FAQ.html) · [Troubleshooting](https://ontosql.readthedocs.io/en/latest/TROUBLESHOOTING.html)

### Examples (repository clone)

The `examples/` directory is **not included in the PyPI wheel**. Clone the repo to run scripts:

```bash
git clone https://github.com/eddiethedean/ontosql.git
cd ontosql && pip install -e ".[dev]"
```

| Script | Extras | What it teaches |
|--------|--------|-----------------|
| [person_org_demo.py](examples/person_org_demo.py) | core | Sync CRUD round-trip |
| [person_org_async.py](examples/person_org_async.py) | `ontosql[async]` | Async session |
| [hybrid_person_org.py](examples/hybrid_person_org.py) | core | Graph sync, import, materialize |
| [person_org_api_production.py](examples/person_org_api_production.py) | `ontosql[fastapi,async]` + `uvicorn` | Production async session pattern |

```bash
python examples/person_org_demo.py
pip install "ontosql[async]" && python examples/person_org_async.py
pip install "ontosql[fastapi,async]" uvicorn && python examples/person_org_api_production.py
```

## Quick start

### 0. Database engine

```python
from sqlmodel import SQLModel, create_engine

engine = create_engine("sqlite:///./app.db")
SQLModel.metadata.create_all(engine)  # use Alembic in production
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
        nested_map=OrganizationMap,
        property="schema:worksFor",
        fk_column=PersonRow.org_id,
    )
```

See [Cascade policies](https://ontosql.readthedocs.io/en/latest/guides/cascade-policies.html) for nested write behavior (`link`, `upsert`, `replace`, `ignore`). Default **`link`** is safest for shared nested entities.

### 4. Session (CRUD)

```python
from sqlmodel import Session

from ontosql import OntoSession, paginate

with Session(engine) as raw:
    raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
    raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
    raw.commit()

with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    ada = session.get(Person, identity=1)
    team = session.find(Person, where=Person.employer.name.startswith("Analytical"))
    page = paginate(session, Person, limit=20, offset=0)

    new_person = session.save(Person.model_construct(name="Grace Hopper", id=None))  # id=None → insert
    new_person.name = "Grace M. Hopper"
    session.save(new_person)
    session.delete(new_person)
```

Async sessions use `AsyncOntoSession` with the same API — see [Async guide](https://ontosql.readthedocs.io/en/latest/getting-started/async.html) and [examples/person_org_async.py](examples/person_org_async.py).

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
- **CascadePolicy** — explicit nested write behavior on `Map.nested` ([guide](https://ontosql.readthedocs.io/en/latest/guides/cascade-policies.html))
- **`Map.computed`** — read-only SQL expressions on semantic fields (0.5.0)
- **`Map.collection`** — many-to-many bridge tables with cascade policies (0.5.0)
- **OntoRouter** (`ontosql[fastapi]`) — auto CRUD routes + content negotiation
- **PrefixRegistry** — CURIE expansion and JSON-LD `@context`
- **Export** — `to_jsonld()` / `to_rdf()` on semantic instances
- **Import** — `ontosql.import_` hydrates `OntoModel` from RDF ([FAQ](https://ontosql.readthedocs.io/en/latest/FAQ.html#import-path-why-ontosqlimport_))
- **Graph sync** — mirror SQL writes to RDF graphs on commit ([Hybrid guide](https://ontosql.readthedocs.io/en/latest/HYBRID.html))
- **SHACL** — generate and validate shapes from maps (`ontosql[shacl]`)
- **Prefix bundles** — `PrefixRegistry.curated("schema_org")` or `curated("dcterms")` for schema.org / DC Terms

## FastAPI

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from ontosql.fastapi import OntoRouter, onto_async_session_lifespan

engine = create_async_engine("sqlite+aiosqlite://")


async def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != "your-secret":  # replace with real auth
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    onto_async_session_lifespan(app, engine, maps=[PersonMap, OrganizationMap])
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
router = OntoRouter(
    maps=[PersonMap, OrganizationMap],
    dependencies=[Depends(require_api_key)],
)
router.register(Person)
router.include_in(app)
```

See [examples/person_org_api_production.py](examples/person_org_api_production.py) for hand-written production routes (no `OntoRouter`).

> **Production:** `OntoRouter` requires `dependencies=[Depends(your_auth)]` before public exposure. See [Production FastAPI](https://ontosql.readthedocs.io/en/latest/guides/production-router.html) and [Security](https://ontosql.readthedocs.io/en/latest/SECURITY.html).

## Documentation

Full site: **[ontosql.readthedocs.io](https://ontosql.readthedocs.io/en/latest/)**

### Getting started

- [Start here](https://ontosql.readthedocs.io/en/latest/guides/start-here.html) — pick your path (CRUD, FastAPI, hybrid graph, production)
- [Installation](https://ontosql.readthedocs.io/en/latest/getting-started/installation.html)
- [Quick start (standalone)](https://ontosql.readthedocs.io/en/latest/getting-started/quickstart.html)
- [Async sessions](https://ontosql.readthedocs.io/en/latest/getting-started/async.html)

### Guides

- [Cascade policies](https://ontosql.readthedocs.io/en/latest/guides/cascade-policies.html)
- [Bridge tables](https://ontosql.readthedocs.io/en/latest/guides/bridge-tables.html) — many-to-many `Map.collection`
- [Multi-map views](https://ontosql.readthedocs.io/en/latest/guides/multi-map-views.html) — one table, multiple semantic entities
- [Postgres dialect](https://ontosql.readthedocs.io/en/latest/guides/postgres-dialect.html) — UUID, JSONB, ARRAY
- [Hybrid SQL + graph](https://ontosql.readthedocs.io/en/latest/HYBRID.html)
- [FAQ](https://ontosql.readthedocs.io/en/latest/FAQ.html)
- [Troubleshooting](https://ontosql.readthedocs.io/en/latest/TROUBLESHOOTING.html)

### Architecture and reference

- [Architecture](https://ontosql.readthedocs.io/en/latest/ARCHITECTURE.html)
- [Ecosystem](https://ontosql.readthedocs.io/en/latest/ECOSYSTEM.html) — OntoSQL, TripleModel, SparqlModel
- [Technical specification](https://ontosql.readthedocs.io/en/latest/SPECS.html)
- [Compatibility](https://ontosql.readthedocs.io/en/latest/COMPATIBILITY.html)
- [Security](https://ontosql.readthedocs.io/en/latest/SECURITY.html)
- [Dependencies](https://ontosql.readthedocs.io/en/latest/DEPS.html)

### Project

- [Roadmap](https://ontosql.readthedocs.io/en/latest/ROADMAP.html)
- [Changelog](https://ontosql.readthedocs.io/en/latest/changelog.html)
- [Contributing](https://ontosql.readthedocs.io/en/latest/contributing.html)
- [Code of Conduct](https://ontosql.readthedocs.io/en/latest/code_of_conduct.html)
- [Releasing](https://ontosql.readthedocs.io/en/latest/RELEASING.html) (maintainers)

## Development

See [Contributing](https://ontosql.readthedocs.io/en/latest/contributing.html) and [Releasing](https://ontosql.readthedocs.io/en/latest/RELEASING.html).

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
