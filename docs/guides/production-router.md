# Production FastAPI patterns

`OntoRouter` is **demo-grade**: sync SQLAlchemy sessions inside `async def` routes, no authentication, and no request size limits by default. Use it for local prototypes only.

For production APIs, wrap OntoSQL with your own auth, rate limits, and observability. This guide shows the recommended wiring.

## Async sessions (required under load)

Use `AsyncOntoSession` with `AsyncSessionDep` so database I/O does not block the event loop:

```python
from sqlalchemy.ext.asyncio import create_async_engine
from ontosql.fastapi.deps import AsyncSessionDep, onto_async_session_lifespan

engine = create_async_engine("postgresql+asyncpg://...")
onto_async_session_lifespan(app, engine, maps=[PersonMap, OrganizationMap])

@app.get("/person/{person_id}")
async def get_person(person_id: int, session: AsyncSessionDep):
    return await session.get(Person, id=person_id)
```

See [examples/person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py) for a minimal runnable app.

## OntoRouter hardening (internal / low-traffic only)

If you still mount `OntoRouter`, pass production-oriented options:

```python
from ontosql.fastapi.router import OntoRouter

router = OntoRouter(
    maps=[PersonMap, OrganizationMap],
    validate_entities=True,   # Person.model_validate instead of model_construct
    max_body_bytes=64 * 1024, # reject oversized POST/PATCH bodies (413)
)
```

| Option | Default | Purpose |
|--------|---------|---------|
| `validate_entities` | `False` | Run `OntoModel.model_validate` on create/patch (semantic validators) |
| `max_body_bytes` | `None` | Cap JSON body size on POST/PATCH |

You still need **your** middleware for auth, rate limits, and structured logging.

## Checklist before exposing HTTP

1. **Authn / authz** on every route
2. **Rate limits** per client / API key
3. **Body size limits** (router `max_body_bytes` or reverse proxy)
4. **`AsyncOntoSession`** per request via dependency injection
5. **`Person.model_validate`** (or `validate_entities=True`) for business rules
6. **Engine pool** — `pool_size`, `pool_timeout`, `pool_pre_ping`, statement timeout
7. **Structured logging** around session enter/exit, save, commit, graph sync
8. **Graph sync** — treat as eventual consistency; see [HYBRID.md](../HYBRID.md#graph-sync-failures-split-brain)

## Related

- [SECURITY.md](../SECURITY.md) — threat model
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) — `rollback_pending` vs SQL rollback
- [examples/person_org_api.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api.py) — minimal demo router
