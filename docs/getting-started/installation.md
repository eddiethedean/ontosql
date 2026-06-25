# Installation

## Requirements

- **Python 3.10+** (3.10, 3.11, 3.12, 3.13 tested in CI)
- A SQL database supported by SQLAlchemy / SQLModel (SQLite, PostgreSQL, etc.)

Core dependencies (installed automatically): `sqlmodel`, `triplemodel`, `typing-extensions`.

## PyPI

```bash
pip install ontosql
```

## Optional extras

| Extra | Install | Purpose |
|-------|---------|---------|
| `fastapi` | `pip install "ontosql[fastapi]"` | `OntoRouter`, content negotiation, `orjson` |
| `jsonld` | `pip install "ontosql[jsonld]"` | PyLD compaction/framing helpers |
| `sparql` | `pip install "ontosql[sparql]"` | `OntoGraphSync` + SparqlModel |
| `shacl` | `pip install "ontosql[shacl]"` | SHACL shape generation + pySHACL validation |

## Development install

From a clone of the repository:

```bash
pip install -e ".[dev]"
```

This installs test tools, all extras, and editable `ontosql`. See [Contributing](../contributing.md).

## Async SQLite

For `AsyncOntoSession` with SQLite:

```bash
pip install aiosqlite greenlet
```

## Verify install

```bash
python -c "import ontosql; print(ontosql.__version__)"
```

## Next steps

- [Quick start](quickstart.md)
- [Architecture](../ARCHITECTURE.md)
