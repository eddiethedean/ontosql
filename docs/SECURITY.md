# Security

## SQL compilation

OntoSQL compiles semantic queries to SQLAlchemy statements with **bound parameters** for values in `where`, `save`, and `delete` plans. User-supplied filter values are passed as parameters, not interpolated into SQL strings.

### `execute_sql()`

`OntoSession.execute_sql(statement, params=...)` runs raw SQL via SQLAlchemy `text()`. **Always use named parameters** — never concatenate user input into `statement`:

```python
# Safe
session.execute_sql("SELECT * FROM people WHERE id = :id", params={"id": user_id})

# Unsafe — do not do this
session.execute_sql(f"SELECT * FROM people WHERE id = {user_id}")
```

## OntoRouter (FastAPI)

`OntoRouter` is **demo-grade**:

| Control | Status |
|---------|--------|
| Authentication | Not provided |
| Authorization | Not provided |
| Rate limiting | Not provided |
| Request body validation | Generated Pydantic models validate POST/PATCH bodies |
| Sync session in async routes | Blocking I/O |

Do not expose `OntoRouter` on public networks without auth middleware, rate limits, and async session wiring for production load.

## Graph sync consistency

When `graph_sync` is configured, graph updates are queued during `save()` / `delete()` and applied **after SQL commit**. If the session rolls back, queued graph updates are discarded. Plan hybrid architectures accordingly — the graph is a derived view, not a two-phase commit with SQL.

See [HYBRID.md](HYBRID.md).

## REPLACE cascade

`CascadePolicy.REPLACE` deletes nested rows when associations change. It refuses to delete nested rows still referenced by other parent rows. Do not use REPLACE for shared entities.

See [guides/cascade-policies.md](guides/cascade-policies.md).

## Reporting vulnerabilities

Please report security issues privately via GitHub Security Advisories or by emailing the maintainers listed on the repository. Do not open public issues for undisclosed vulnerabilities.
