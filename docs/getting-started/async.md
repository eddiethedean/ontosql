# Async sessions

`AsyncOntoSession` mirrors the synchronous API with `async with` and `await`.

## Install

```bash
pip install "ontosql[async]"
```

For PostgreSQL, use `asyncpg` with `create_async_engine("postgresql+asyncpg://...")`.

## Example

See [examples/person_org_async.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_async.py):

```python
from sqlalchemy.ext.asyncio import create_async_engine
from ontosql import AsyncOntoSession

engine = create_async_engine("sqlite+aiosqlite://")

async with AsyncOntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    person = await session.get(Person, identity=1)
    person.name = "Updated"
    await session.save(person)
```

## FastAPI

`ontosql.fastapi` exposes `AsyncSessionDep` and `get_async_onto_session` for async route handlers. Wire `onto_session_lifespan` with an `AsyncEngine` and use `AsyncSessionDep` instead of `SessionDep`.

`OntoRouter` currently uses the **synchronous** `OntoSession` inside async handlers (blocking I/O). For production async APIs, prefer custom routes with `AsyncOntoSession`.

## Graph sync

`graph_sync` behavior is the same as sync sessions: updates are queued during `save()` / `delete()` and applied after commit on `__aexit__`.
