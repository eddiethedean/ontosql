# Troubleshooting

## `ModuleNotFoundError: tests.models`

Examples use `examples/models.py`, not `tests.models`. Run:

```bash
python examples/person_org_demo.py
```

Or follow [getting-started/quickstart.md](getting-started/quickstart.md).

## `NameError: name 'engine' is not defined`

Create an engine and tables before `OntoSession`:

```python
from sqlmodel import SQLModel, create_engine

engine = create_engine("sqlite:///./app.db")
SQLModel.metadata.create_all(engine)
```

## `NameError: PersonMap` / `Person` in async or FastAPI docs

Use the full self-contained scripts in [async sessions](getting-started/async.md) or [FastAPI quick start](guides/fastapi-quickstart.md), or complete [quick start](getting-started/quickstart.md) Tier 1 first.

## `KeyError: No mapper registered for entity type`

Pass mappers to the session: `OntoSession(engine, maps=[PersonMap, OrganizationMap])`.

## `ExecuteError: Cannot REPLACE nested ... still referenced` {#executeerror-replace-nested}

Another row still references the nested entity you tried to delete. Use `CascadePolicy.LINK` or `IGNORE` for shared nested rows. See [guides/cascade-policies.md](guides/cascade-policies.md).

## `WriteCompileError` on save

Common causes:

- Updating a **computed** field (`Map.computed`) — computed fields are read-only
- Partial update touched a field that does not map to a column

## `CompileError` in `where` clause

Raw `sqlalchemy.text()` is rejected in semantic filters. Use semantic field expressions — see [semantic queries](guides/semantic-queries.md).

## `OntoImportError` on RDF import

- Subject missing required `rdf:type`
- Ambiguous subjects when `iri=` omitted and multiple matches exist
- Invalid literal coercion (bad int/bool strings)
- Circular nested references in RDF
- Payload exceeds `max_bytes` or `max_triples`

Use explicit `iri=` or ensure a single subject of the expected type. Set `untrusted=True` on public import paths.

## `from ontosql.import import ...` SyntaxError

Use `from ontosql.import_ import ...` (trailing underscore).

## Graph out of sync with SQL

Graph sync runs at **commit**, not immediately on `save()`. Check inside the session before exit — graph may still be empty. Rolled-back transactions do not update the graph.

If graph sync fails after SQL commit, you have a **split-brain** risk: SQL is durable, graph may be partial. Check `session.graph_sync_pending` and `session.graph_sync_failures`, then call `session.retry_graph_sync()` after fixing the graph target. See [HYBRID.md](HYBRID.md#graph-sync-failures-split-brain) and [graph sync operations runbook](guides/graph-sync-operations.md).

## `GraphSyncError` after commit

SQL committed successfully; graph sync failed partway. Fix the graph target and call `session.retry_graph_sync()`. See [HYBRID.md](HYBRID.md#graph-sync-failures-split-brain).

## `clear_pending()` vs SQL rollback

| Method | Effect |
|--------|--------|
| `clear_pending()` | Clears queued save/delete plans and graph sync queues only — **does not** undo flushed SQL |
| `session.rollback()` (sync) | Rolls back the open SQLAlchemy transaction |
| Exit `with` on exception | SQL rollback; graph queue discarded |

## `OntoSession` raises "not active"

Sync `OntoSession` must be used as a context manager: `with OntoSession(engine, maps=[...]) as session:`. The SQLAlchemy connection opens in `__enter__` and closes in `__exit__`.

## `OntoRouter` returns 422

POST/PATCH bodies are validated against generated Pydantic models. Ensure field types match the semantic model (e.g. nested `employer` shape).

## `OntoRouter` returns 401

Pass `dependencies=[Depends(your_auth)]` and send required credentials (e.g. `X-API-Key` header in examples).

## Async session `RuntimeError: not active`

Use `async with AsyncOntoSession(...) as session:` before calling session methods.

## SQLite foreign key errors with REPLACE cascade

Enable foreign keys in production:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _fk_pragma(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
```

See [COMPATIBILITY.md](COMPATIBILITY.md).

## Still stuck?

Open an issue with minimal reproduction code. See [Contributing](contributing.md).

## Error catalog

| Exception | Typical cause | Fix |
|-----------|---------------|-----|
| `OntoImportError` | RDF/JSON-LD hydration failed | [RDF import](#ontoimporterror-on-rdf-import) |
| `GraphSyncError` | Post-commit graph sync failed | [Graph sync](#graphsyncerror-after-commit) |
| `ExecuteError` | Unsafe delete or REPLACE conflict | [REPLACE](#executeerror-replace-nested) |
| `WriteCompileError` | Invalid save (computed field, etc.) | [Write compile](#writecompileerror-on-save) |
| `CompileError` | Invalid semantic filter | [CompileError](#compileerror-in-where-clause) |
| `KeyError` (mapper) | Missing `maps=[...]` | [Mapper registration](#keyerror-no-mapper-registered-for-entity-type) |
