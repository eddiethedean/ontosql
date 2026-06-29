# Async sessions

`AsyncOntoSession` mirrors the synchronous API with `async with` and `await`.

## Install

```bash
pip install "ontosql[async]"
```

For PostgreSQL, use `asyncpg` with `create_async_engine("postgresql+asyncpg://...")`.

## Runnable example

Save as `async_demo.py` and run with `python async_demo.py` (requires Python 3.10+):

```python
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, Session, SQLModel

from ontosql import AsyncOntoSession, Map, OntoMapper, OntoModel, onto_property

# --- physical ---
class OrgRow(SQLModel, table=True):
    __tablename__ = "orgs"
    id: int | None = Field(default=None, primary_key=True)
    name: str

class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    org_id: int | None = Field(default=None, foreign_key="orgs.id")

# --- semantic ---
class Organization(OntoModel):
    type_iri = "schema:Organization"
    iri_template = "https://data.example.org/org/{id}"
    id: int
    name: str = onto_property("schema:name")

class Person(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"
    id: int
    name: str = onto_property("schema:name")
    employer: Organization | None = onto_property("schema:worksFor")

# --- maps ---
class OrganizationMap(OntoMapper[Organization]):
    entity = Organization
    id = Map(OrgRow.id)
    name = Map(OrgRow.name, property="schema:name")

class PersonMap(OntoMapper[Person]):
    entity = Person
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")
    employer = Map.nested(
        Organization,
        join=PersonRow.org_id == OrgRow.id,
        nested_map=OrganizationMap,
        property="schema:worksFor",
        fk_column=PersonRow.org_id,
    )

async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")

    def setup(connection) -> None:
        SQLModel.metadata.create_all(connection)
        with Session(connection) as s:
            s.add(OrgRow(id=10, name="Analytical Engines Inc."))
            s.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
            s.commit()

    async with engine.begin() as conn:
        await conn.run_sync(setup)

    async with AsyncOntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
        person = await session.get(Person, identity=1)
        assert person is not None
        print(person.name, "→", person.employer.name if person.employer else "")
        person.name = "Ada L."
        await session.save(person)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
```

The seed step uses SQLAlchemy Core inserts so the example is fully async. For simpler seeding in apps, use a sync `Session` with `create_engine` once at startup, or reuse models from the [quick start](quickstart.md).

## Repository example

See [examples/person_org_async.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_async.py) for the shared `examples/models.py` pattern.

## FastAPI

`ontosql.fastapi` exposes `AsyncSessionDep` and `get_async_onto_session`. Wire `onto_async_session_lifespan` with an `AsyncEngine`.

`OntoRouter` uses `AsyncSessionDep` on all routes. See [FastAPI quick start](../guides/fastapi-quickstart.md) and [production-router](../guides/production-router.md).

## Graph sync

`graph_sync` behavior matches sync sessions: updates queue on `save()` / `delete()` and apply after commit on `__aexit__`.
