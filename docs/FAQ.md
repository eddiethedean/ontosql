# FAQ

## Why two model layers (SQLModel + OntoModel)?

Physical `SQLModel` tables mirror your database schema (migrations, FKs, legacy columns). Semantic `OntoModel` types are what application code uses — composed, validated, ontology-shaped. `OntoMapper` connects them explicitly. See [ARCHITECTURE.md](ARCHITECTURE.md).

## Do I need RDF / schema.org IRIs if I only want SQL CRUD?

No. Tier 1 of the [quick start](getting-started/quickstart.md) uses semantic CRUD only. `type_iri` and `iri_template` enable export later; they do not require a graph database.

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

## How do partial updates work on `save()`?

On update, only fields in `instance.model_fields_set` that map to columns are written (Pydantic "touched fields" semantics). Unset fields are not overwritten.

Use `Person.model_construct(...)` with only the fields you intend to change, or mutate attributes on an instance loaded via `get()` / `find()` then call `save()`.

See [session lifecycle (internals)](internals/session-lifecycle.md).

## Can I use OntoSQL with existing SQLAlchemy models?

Physical models must be SQLModel classes with `table=True` so OntoSQL can read column metadata for `Map` bindings. You can wrap existing tables by defining matching SQLModel row classes alongside your current models.

OntoSQL does not auto-generate maps from SQLAlchemy `Table` objects.

## Who owns schema migrations?

**You do.** OntoSQL compiles CRUD against your SQLModel tables but does not run Alembic or create migrations. Migrate physical tables with Alembic (or your tool); keep `OntoMapper` bindings in sync with column changes.

## When does graph sync update the RDF graph?

Graph sync is **queued** on `save()` and `delete()`, then applied **after the SQL transaction commits** when the session context exits. Rolled-back sessions do not update the graph. See [HYBRID.md](HYBRID.md).

## `link` vs `upsert` vs `replace`?

See [guides/cascade-policies.md](guides/cascade-policies.md). Default is `link` — safest for shared nested entities.

## Can I use one SQL table for multiple semantic types?

Yes — define multiple `OntoMapper` classes for the same physical table with different semantic entities. See [multi-map views](guides/multi-map-views.md).

## Does OntoSQL run OWL reasoning?

No. Export/import target JSON-LD and RDF serializations; optional SHACL validates shape constraints, not full reasoning.

## SQLite vs PostgreSQL?

Both work. CI runs the full test matrix on **SQLite** (Python 3.10–3.13) and a dedicated **PostgreSQL** job for session CRUD ([`test_postgres.py`](https://github.com/eddiethedean/ontosql/blob/main/tests/test_postgres.py)). Enable foreign keys on SQLite in production if you rely on FK constraints with REPLACE cascade. Postgres is recommended for production relational workloads. See [guides/postgres-dialect.md](guides/postgres-dialect.md).

## Is OntoSQL 1.0 stable?

Not yet. **0.5.x is beta** (PyPI classifier: Development Status :: 4 - Beta). API stability tiers are in [SPECS.md](SPECS.md). Semver guarantees begin at **1.0**. Pin versions and read [Compatibility](COMPATIBILITY.md) before upgrading.

## Where is the API reference?

- **Generated API:** [Session](reference/session.md) · [Mapping](reference/mapping.md) · [Query](reference/query.md) · [I/O](reference/io.md) · [FastAPI](reference/fastapi.md) · [Export](reference/export.md) · [Import](reference/import.md) · [Sync](reference/sync.md) · [SHACL](reference/shacl.md)
- **Contract:** [SPECS.md](SPECS.md) — module layout and stability tiers
- **Hosted site:** [ontosql.readthedocs.io](https://ontosql.readthedocs.io/en/latest/)

## Is there enterprise or commercial support?

Not in 0.5.x. See [SUPPORT.md](SUPPORT.md) and [enterprise adoption](enterprise-adoption.md).
