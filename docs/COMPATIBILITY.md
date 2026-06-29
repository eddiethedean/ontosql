# Compatibility

## Python

| Version | Support |
|---------|---------|
| 3.10 | Supported (CI) |
| 3.11 | Supported (CI) |
| 3.12 | Supported (CI) |
| 3.13 | Supported (CI) |
| &lt; 3.10 | Not supported |

## Core runtime dependencies

Declared in [pyproject.toml](https://github.com/eddiethedean/ontosql/blob/main/pyproject.toml):

| Package | Constraint | Tested range (CI) | Role |
|---------|------------|-------------------|------|
| sqlmodel | `>=0.0.14` | 0.0.14+ (via pip resolve) | Physical models, engine integration |
| triplemodel | `>=0.12.0` | 0.12.0+ (via pip resolve) | RDF export, CURIE expansion |
| typing-extensions | `>=4.0` | 4.x | Typing backports |

SQLAlchemy and Pydantic are transitive via SQLModel. Pin and test your target SQLModel/Pydantic major versions in staging before production deploys.

OntoSQL does not cap upper bounds on core dependencies in 0.5.x; verify upgrades in a staging environment.

## Optional extras

| Extra | Key packages | Notes |
|-------|----------------|-------|
| `async` | aiosqlite `>=0.20`, greenlet `>=3.0` | `AsyncOntoSession` with SQLite |
| `fastapi` | fastapi `>=0.100`, orjson `>=3.9` | `OntoRouter` (async; requires auth `dependencies` for public exposure) |
| `jsonld` | PyLD `>=3.0` | Compaction and framing |
| `sparql` | sparqlmodel `>=0.13.1` | Graph sync adapter |
| `shacl` | pyshacl `>=0.29` | Shape generation and validation |

## Development status

PyPI classifier: **Development Status :: 4 - Beta** (0.5.x). API may evolve until 1.0; see [ROADMAP.md](ROADMAP.md) and the API stability section in [SPECS.md](SPECS.md).

## Databases

| Database | CI coverage | Production notes |
|----------|-------------|------------------|
| **SQLite** | Full test matrix (Python 3.10–3.13) | Enable `PRAGMA foreign_keys=ON` for FK enforcement with REPLACE cascade |
| **PostgreSQL** | Dedicated CI job ([`test_postgres.py`](https://github.com/eddiethedean/ontosql/blob/main/tests/test_postgres.py)) — session CRUD, nested reads, save/delete | Recommended for production; see [postgres-dialect.md](guides/postgres-dialect.md) |

Other SQLAlchemy-supported databases may work but are not CI-tested.

## Ecosystem alignment

| Package | Notes |
|---------|-------|
| TripleModel | Core RDF dependency — use `triplemodel.Store` for graph manipulation in app code |
| SparqlModel | Optional via `ontosql[sparql]` |

For RDF graph operations, prefer **TripleModel** APIs over direct **pyoxigraph** imports (pyoxigraph is a transitive implementation detail).

See [ECOSYSTEM.md](ECOSYSTEM.md) and [DEPS.md](DEPS.md).
