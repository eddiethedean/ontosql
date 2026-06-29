# FAQ

## Why two model layers (SQLModel + OntoModel)?

Physical `SQLModel` tables mirror your database schema (migrations, FKs, legacy columns). Semantic `OntoModel` types are what application code uses — composed, validated, ontology-shaped. `OntoMapper` connects them explicitly. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Import path: why `ontosql.import_`?

`import` is a Python keyword. The public module is `ontosql.import_` (trailing underscore):

```python
from ontosql.import_ import import_from_jsonld, import_from_rdf
```

## Why doesn't my quick start run?

You need a SQLAlchemy `engine` and tables before `OntoSession`:

```python
engine = create_engine("sqlite:///./app.db")
SQLModel.metadata.create_all(engine)
```

See [getting-started/quickstart.md](getting-started/quickstart.md).

## When does graph sync update the RDF graph?

Graph sync is **queued** on `save()` and `delete()`, then applied **after the SQL transaction commits** when the session context exits. Rolled-back sessions do not update the graph. See [HYBRID.md](HYBRID.md).

## `link` vs `upsert` vs `replace`?

See [guides/cascade-policies.md](guides/cascade-policies.md). Default is `link` — safest for shared nested entities.

## Can I use one SQL table for multiple semantic types?

Yes — define multiple `OntoMapper` classes for the same physical table with different semantic entities.

## Does OntoSQL run OWL reasoning?

No. Export/import target JSON-LD and RDF serializations; optional SHACL validates shape constraints, not full reasoning.

## SQLite vs PostgreSQL?

Both work. CI runs the full test matrix on **SQLite** (Python 3.10–3.13) and a dedicated **PostgreSQL** job for session CRUD ([`test_postgres.py`](https://github.com/eddiethedean/ontosql/blob/main/tests/test_postgres.py)). Enable foreign keys on SQLite in production if you rely on FK constraints with REPLACE cascade. Postgres is recommended for production relational workloads. See [guides/postgres-dialect.md](guides/postgres-dialect.md).

## Where is the API reference?

- **Hosted docs:** [https://ontosql.readthedocs.io/](https://ontosql.readthedocs.io/) (also mirrored on [GitHub Pages](https://eddiethedean.github.io/ontosql/))
- **Contract:** [SPECS.md](SPECS.md) — module layout and stability tiers
- Generated API docs from docstrings are planned for 0.9
