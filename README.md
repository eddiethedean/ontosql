# OntoSQL

[![PyPI version](https://img.shields.io/pypi/v/ontosql)](https://pypi.org/project/ontosql/)
[![CI](https://github.com/eddiethedean/ontosql/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ontosql/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/ontosql)](https://pypi.org/project/ontosql/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Documentation](https://readthedocs.org/projects/ontosql/badge/?version=latest)](https://ontosql.readthedocs.io/en/latest/)

**Semantic CRUD for SQL-first Python apps** — SQLModel tables, Pydantic ontology models, explicit mappers, optional JSON-LD/RDF export.

> **0.5.x beta** — API stability tiers in [SPECS](https://ontosql.readthedocs.io/en/latest/SPECS.html); semver guarantees begin at 1.0. Pin versions in production.

> **Not** a SPARQL database or OBDA query engine. RDF and graph sync are optional extras.

Real databases rarely match ontology shapes one-to-one. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with explicit **mappers**. Application code uses semantic types; OntoSQL compiles SQL on the backend.

## Install

```bash
pip install ontosql
pip install "ontosql[async,fastapi]"   # optional extras — see docs
```

**Requirements:** Python 3.10+. See [Compatibility](https://ontosql.readthedocs.io/en/latest/COMPATIBILITY.html).

## Start here

| I want to… | Go to |
|------------|-------|
| Try CRUD in 5 minutes (pip only) | [Quick start](https://ontosql.readthedocs.io/en/latest/getting-started/quickstart.html) |
| Pick a path (async, FastAPI, hybrid) | [Start here](https://ontosql.readthedocs.io/en/latest/guides/start-here.html) |
| Understand the design | [Architecture](https://ontosql.readthedocs.io/en/latest/ARCHITECTURE.html) |
| Decide if OntoSQL fits | [When to use OntoSQL](https://ontosql.readthedocs.io/en/latest/getting-started/when-to-use.html) |
| Evaluate for production | [Security](https://ontosql.readthedocs.io/en/latest/SECURITY.html) · [Compatibility](https://ontosql.readthedocs.io/en/latest/COMPATIBILITY.html) |

**Full docs:** [ontosql.readthedocs.io](https://ontosql.readthedocs.io/en/latest/)

## Minimal example

```python
from sqlmodel import Field, Session, SQLModel, create_engine
from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property

class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str

class Person(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"
    id: int
    name: str = onto_property("schema:name")

class PersonMap(OntoMapper[Person]):
    entity = Person
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")

engine = create_engine("sqlite://")
SQLModel.metadata.create_all(engine)
with Session(engine) as raw:
    raw.add(PersonRow(id=1, name="Ada Lovelace"))
    raw.commit()

with OntoSession(engine, maps=[PersonMap]) as session:
    print(session.get(Person, identity=1).name)
```

Copy the full Person/Organization walkthrough from the [quick start](https://ontosql.readthedocs.io/en/latest/getting-started/quickstart.html).

## Ecosystem

Optional RDF export uses [TripleModel](https://github.com/eddiethedean/triplemodel). Graph-native apps can pair OntoSQL with [SparqlModel](https://github.com/eddiethedean/sparqlmodel). See [Ecosystem](https://ontosql.readthedocs.io/en/latest/ECOSYSTEM.html).

## Examples (repository clone)

The `examples/` directory is **not** in the PyPI wheel:

```bash
git clone https://github.com/eddiethedean/ontosql.git
cd ontosql && pip install -e ".[dev]"
python examples/person_org_demo.py
```

| Script | What it teaches |
|--------|-----------------|
| [person_org_demo.py](examples/person_org_demo.py) | Sync CRUD round-trip |
| [person_org_async.py](examples/person_org_async.py) | Async session |
| [hybrid_person_org.py](examples/hybrid_person_org.py) | Graph sync, import |
| [person_org_api_production.py](examples/person_org_api_production.py) | Production FastAPI pattern |

## Development

```bash
pip install -e ".[dev]"
ruff check src tests && ty check && pytest --cov=ontosql --cov-fail-under=90
```

See [Contributing](https://ontosql.readthedocs.io/en/latest/contributing.html) and [Releasing](https://ontosql.readthedocs.io/en/latest/RELEASING.html).

## License

MIT — see [LICENSE](LICENSE).
