# FastAPI quick start

Self-contained minimal API with `OntoRouter` — copy into `app.py` and run with uvicorn. Requires `pip install "ontosql[fastapi,async]" uvicorn`.

!!! warning "Development only"

    This example uses a hard-coded API key. Before internet exposure, read [production-router.md](production-router.md) and [SECURITY.md](../SECURITY.md).

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, Session, SQLModel

from ontosql import Map, OntoMapper, OntoModel, onto_property
from ontosql.fastapi import OntoRouter, onto_async_session_lifespan

# --- physical ---
class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str

# --- semantic ---
class Person(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"
    id: int
    name: str = onto_property("schema:name")

class PersonMap(OntoMapper[Person]):
    entity = Person
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")

engine = create_async_engine("sqlite+aiosqlite://")

async def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != "dev-secret":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    def seed(connection) -> None:
        with Session(connection) as s:
            if not s.get(PersonRow, 1):
                s.add(PersonRow(id=1, name="Ada Lovelace"))
                s.commit()

    async with engine.begin() as conn:
        await conn.run_sync(seed)

    onto_async_session_lifespan(app, engine, maps=[PersonMap])
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
router = OntoRouter(
    maps=[PersonMap],
    dependencies=[Depends(require_api_key)],
)
router.register(Person)
router.include_in(app)
```

Run:

```bash
uvicorn app:app --reload
curl -H "X-API-Key: dev-secret" http://127.0.0.1:8000/person/1
curl -H "X-API-Key: dev-secret" -H "Accept: text/turtle" http://127.0.0.1:8000/person/1
```

## Hand-written routes

For production control (custom auth, pagination, observability), see [examples/person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py) and [production-router.md](production-router.md).

## Read next

- [Async sessions](../getting-started/async.md)
- [Semantic queries](semantic-queries.md)
- [API reference](../reference/session.md)
