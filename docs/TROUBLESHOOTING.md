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

## `KeyError: No mapper registered for entity type`

Pass mappers to the session: `OntoSession(engine, maps=[PersonMap, OrganizationMap])`.

## `ExecuteError: Cannot REPLACE nested ... still referenced`

Another row still references the nested entity you tried to delete. Use `CascadePolicy.LINK` or `IGNORE` for shared nested rows. See [guides/cascade-policies.md](guides/cascade-policies.md).

## `OntoImportError` on RDF import

- Subject missing required `rdf:type`
- Ambiguous subjects when `iri=` omitted and multiple matches exist
- Invalid literal coercion (bad int/bool strings)
- Circular nested references in RDF

Use explicit `iri=` or ensure a single subject of the expected type.

## `from ontosql.import import ...` SyntaxError

Use `from ontosql.import_ import ...` (trailing underscore).

## Graph out of sync with SQL

Graph sync runs at **commit**, not immediately on `save()`. Check inside the session before exit — graph may still be empty. Rolled-back transactions do not update the graph.

If graph sync fails after SQL commit, you have a **split-brain** risk: SQL is durable, graph may be partial. Check `session.graph_sync_pending` and `session.graph_sync_failures`, then call `session.retry_graph_sync()` after fixing the graph target. See [HYBRID.md](HYBRID.md#graph-sync-failures-split-brain).

## `rollback_pending()` vs SQL rollback

| Method | Effect |
|--------|--------|
| `rollback_pending()` | Clears queued save/delete plans and graph sync queues only — **does not** undo flushed SQL |
| `session.rollback()` (sync) | Rolls back the open SQLAlchemy transaction |
| Exit `with` on exception | SQL rollback; graph queue discarded |

## `OntoSession` raises "not active"

Sync `OntoSession` must be used as a context manager: `with OntoSession(engine, maps=[...]) as session:`. The SQLAlchemy connection opens in `__enter__` and closes in `__exit__`.

## `OntoRouter` returns 422

POST/PATCH bodies are validated against generated Pydantic models. Ensure field types match the semantic model (e.g. nested `employer` shape).

## Async session `RuntimeError: not active`

Use `async with AsyncOntoSession(...) as session:` before calling session methods.

## Still stuck?

Open an issue with minimal reproduction code. See [Contributing](contributing.md).
