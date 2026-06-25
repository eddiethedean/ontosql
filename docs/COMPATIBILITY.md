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

| Package | Constraint | Role |
|---------|------------|------|
| sqlmodel | `>=0.0.14` | Physical models, engine integration |
| triplemodel | `>=0.12.0` | RDF export, CURIE expansion |
| typing-extensions | `>=4.0` | Typing backports |

SQLAlchemy and Pydantic are transitive via SQLModel. Test your target SQLModel/Pydantic major versions in staging.

## Optional extras

| Extra | Key packages |
|-------|----------------|
| `fastapi` | fastapi `>=0.100`, orjson `>=3.9` |
| `jsonld` | PyLD `>=3.0` |
| `sparql` | sparqlmodel `>=0.13.1` |
| `shacl` | pyshacl `>=0.29` |

## Development status

PyPI classifier: **Development Status :: 4 - Beta** (0.4.x). API may evolve until 1.0; see [ROADMAP.md](ROADMAP.md).

## Databases

- **SQLite** — full CI coverage; enable `PRAGMA foreign_keys=ON` for FK enforcement with REPLACE cascade
- **PostgreSQL** — recommended for production; not in default CI matrix but SQLAlchemy-compatible

## Ecosystem alignment

| Package | Notes |
|---------|-------|
| TripleModel | Core RDF dependency |
| SparqlModel | Optional via `ontosql[sparql]` |

See [ECOSYSTEM.md](ECOSYSTEM.md) and [DEPS.md](DEPS.md).
