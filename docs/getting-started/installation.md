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
| `async` | `pip install "ontosql[async]"` | `AsyncOntoSession` with SQLite (`aiosqlite`, `greenlet`) |
| `fastapi` | `pip install "ontosql[fastapi]"` | `OntoRouter`, content negotiation, `orjson` |
| `jsonld` | `pip install "ontosql[jsonld]"` | PyLD compaction/framing helpers |
| `sparql` | `pip install "ontosql[sparql]"` | `OntoGraphSync` + SparqlModel |
| `shacl` | `pip install "ontosql[shacl]"` | SHACL shape generation + pySHACL validation |

Combine extras:

```bash
pip install "ontosql[fastapi,async,shacl]"
```

## Development install

From a clone of the repository:

```bash
pip install -e ".[dev]"
```

This installs test tools, all extras, and editable `ontosql`. See [Contributing](../contributing.md).

## Verify install

```bash
python -c "import ontosql; print(ontosql.__version__)"
```

### Smoke test (optional)

Confirms SQL compile + session work in-memory:

```bash
python -c "
from sqlmodel import Field, Session, SQLModel, create_engine
from ontosql import Map, OntoMapper, OntoModel, OntoSession, onto_property

class Row(SQLModel, table=True):
    __tablename__ = 't'
    id: int | None = Field(default=None, primary_key=True)
    name: str

class M(OntoModel):
    type_iri = 'schema:Thing'
    iri_template = 'https://example.org/t/{id}'
    id: int
    name: str = onto_property('schema:name')

class RowMap(OntoMapper[M]):
    entity = M
    id = Map(Row.id)
    name = Map(Row.name, property='schema:name')

engine = create_engine('sqlite://')
SQLModel.metadata.create_all(engine)
with Session(engine) as s:
    s.add(Row(id=1, name='ok'))
    s.commit()
with OntoSession(engine, maps=[RowMap]) as session:
    assert session.get(M, identity=1).name == 'ok'
print('ok')
"
```

## Next steps

- [Quick start](quickstart.md) — pip-only path (no clone)
- [Architecture](../ARCHITECTURE.md)
