# Production FastAPI patterns

`OntoRouter` is **not safe for public internet** without authentication, authorization, and rate limits. It now defaults to async sessions, semantic validation, and a 64 KiB body cap — but those defaults do **not** replace authn/authz.

For production APIs, wrap OntoSQL with your own auth, rate limits, and observability. This guide shows the recommended wiring.

## Authentication (required)

`OntoRouter` accepts FastAPI `dependencies` applied to every CRUD route. **Do not expose the router without them** on a reachable network:

```python
from fastapi import Depends, Header, HTTPException, status
from ontosql.fastapi.router import OntoRouter

async def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

router = OntoRouter(
    maps=[PersonMap, OrganizationMap],
    dependencies=[Depends(require_api_key)],
)
```

Add **object-level authorization** inside your dependencies or route wrappers: verify the caller may read/write `{entity_id}` and any nested associations in POST/PATCH bodies.

Disable or protect `/docs` and `/openapi.json` in production.

## Async sessions (required)

`OntoRouter` uses `AsyncSessionDep` on all routes. Wire an async engine at startup:

```python
from sqlalchemy.ext.asyncio import create_async_engine
from ontosql.fastapi.deps import onto_async_session_lifespan

engine = create_async_engine("postgresql+asyncpg://...")
onto_async_session_lifespan(app, engine, maps=[PersonMap, OrganizationMap])
```

See [examples/person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py) for a minimal runnable app.

## OntoRouter options

```python
from ontosql.fastapi.router import DEFAULT_MAX_BODY_BYTES, OntoRouter

router = OntoRouter(
    maps=[PersonMap, OrganizationMap],
    validate_entities=True,       # default — OntoModel.model_validate on create/patch
    max_body_bytes=DEFAULT_MAX_BODY_BYTES,  # default 64 KiB; 413 when exceeded
    dependencies=[Depends(require_api_key)],
)
```

| Option | Default | Purpose |
|--------|---------|---------|
| `validate_entities` | `True` | Run `OntoModel.model_validate` on create/patch |
| `max_body_bytes` | `65536` | Cap JSON body size on POST/PATCH |
| `dependencies` | `[]` | **Required for internet** — authn/authz `Depends` |

You still need **your** middleware for rate limits and structured logging.

## RDF import on public endpoints

If you expose RDF import, use guarded calls:

```python
from ontosql.import_ import import_from_rdf

instance = import_from_rdf(
    payload,
    PersonMap,
    format="turtle",
    untrusted=True,  # applies UNTRUSTED_DEFAULT_MAX_BYTES / MAX_TRIPLES
)
```

Always authenticate import routes. `max_triples` alone does not prevent parse-time expansion — see [SECURITY.md](../SECURITY.md#rdf-import-limits).

## Checklist before exposing HTTP

1. **Authn / authz** on every route (`dependencies=` + object-level checks)
2. **Rate limits** per client / API key
3. **Body size limits** (router default + reverse proxy)
4. **`onto_async_session_lifespan`** with `AsyncEngine`
5. **`validate_entities=True`** (default) for business rules
6. **Engine pool** — `pool_size`, `pool_timeout`, `pool_pre_ping`, statement timeout
7. **Structured logging** around session enter/exit, save, commit, graph sync
8. **Graph sync** — treat as eventual consistency; see [HYBRID.md](../HYBRID.md#graph-sync-failures-split-brain)

## Related

- [SECURITY.md](../SECURITY.md) — threat model
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) — `clear_pending` vs SQL rollback
- [examples/person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py) — production async pattern
