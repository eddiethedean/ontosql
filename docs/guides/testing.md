# Testing OntoSQL in your application

Guide for **adopters** validating OntoSQL in CI and staging — not contributor setup (see [contributing.md](../contributing.md)).

## Minimum test stack

```bash
pip install ontosql pytest pytest-asyncio
# optional
pip install "ontosql[async,fastapi]" httpx pytest-cov
```

## In-memory SQLite (fast default)

Use for unit and integration tests without external services:

```python
from sqlmodel import SQLModel, create_engine
from ontosql import OntoSession

@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)

# Define PersonMap / OrganizationMap in your test module or conftest
# (see examples/models.py or the quick start Tier 1 script).

def test_get_person(engine, PersonMap, OrganizationMap):
    with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
        ...
```

Enable foreign keys if testing `REPLACE` cascade:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _fk(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
```

## Postgres integration tests

OntoSQL CI runs Postgres session tests when `ONTO_TEST_DATABASE_URL` is set:

```bash
export ONTO_TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/ontosql_test"
pytest tests/test_postgres.py -v   # reference tests in the repo
```

Mirror this in your pipeline for dialect-specific behavior (UUID, JSONB, concurrent sessions).

## What to test

| Area | Suggested tests |
|------|-----------------|
| **Mapper wiring** | Round-trip `save` → `get` for each entity |
| **Nested writes** | Each `cascade` policy you use (`link`, `upsert`, `replace`) |
| **Partial updates** | `model_fields_set` — only touched fields persist |
| **Semantic queries** | Filters on nested `FieldPath` used in production |
| **Collections** | Many-to-many bridge if using `Map.collection` |
| **Async parity** | Same scenarios with `AsyncOntoSession` if you use async |
| **FastAPI** | Auth dependency rejects unauthenticated calls; 413 on oversized body |
| **Graph sync** | Mock or test store; assert graph updates **after** commit exit |

## FastAPI testing

```python
from httpx import ASGITransport, AsyncClient

@pytest.mark.asyncio
async def test_list_requires_auth(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/onto/person")  # routes use lowercase entity names
        assert r.status_code == 401
```

Wire `OntoRouter(..., dependencies=[Depends(require_api_key)])` as in [production-router.md](production-router.md).

## Contract / regression testing

Until 1.0 API freeze:

- Pin `ontosql==X.Y.Z` in requirements
- Run your integration suite on every upgrade
- Review [CHANGELOG](../changelog.md) and [upgrading.md](upgrading.md)

Public API contract is documented in [SPECS.md](../SPECS.md); generated reference: [Session](../reference/session.md), [Mapping](../reference/mapping.md), [Query](../reference/query.md), [I/O](../reference/io.md).

## Performance testing

OntoSQL publishes **no official benchmarks** in 0.5.x. For load testing:

- Measure your mappers' `find` with production-like joins and collection fields
- Watch N+1 on `Map.collection` — batched in 0.5.0 but still one query per collection field
- Plan your own SLOs; benchmarks planned for 0.9 — [ROADMAP.md](../ROADMAP.md)

## CI checklist

- [ ] SQLite integration tests on every PR
- [ ] Postgres job for release branches (optional for PRs)
- [ ] `ruff` / typecheck on app code using OntoSQL types
- [ ] Pin OntoSQL version in lockfile or constraints file

## Related

- [contributing.md](../contributing.md) — OntoSQL project CI
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- [enterprise adoption](../enterprise-adoption.md)
