# Postgres dialect notes

OntoSQL compiles to SQLAlchemy and works with Postgres via the same `OntoSession` / `OntoMapper` APIs. This guide covers common Postgres column types. **CI tests use SQLite**; validate Postgres-specific snippets against your database.

## UUID columns

```python
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, SQLModel

class UserRow(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True),
    )
```

Map to a semantic `uuid.UUID` or `str` field:

```python
class User(OntoModel):
    id: uuid.UUID
    ...

class UserMap(OntoMapper[User]):
    entity = User
    id = Map(UserRow.id)
```

Use Alembic for migrations; generate UUIDs in application code or with `server_default=gen_random_uuid()`.

## JSONB columns

**Whole document** — map the column directly when the semantic field mirrors the JSON object:

```python
meta: dict[str, Any] = onto_property("ex:metadata")

meta = Map(UserRow.meta, property="ex:metadata")
```

**Scalar path (read-only)** — use `Map.computed` for extracted keys:

```python
from sqlalchemy import cast, String

display_name = Map.computed(
    cast(UserRow.meta["displayName"].astext, String),
    field="displayName",
    property="schema:name",
)
```

Computed fields are not persisted on `save()`; update the underlying JSONB column via a mapped field or raw SQL when needed.

## ARRAY columns

```python
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY

class TagRow(SQLModel, table=True):
    __tablename__ = "tags"
    id: int | None = Field(default=None, primary_key=True)
    labels: list[str] = Field(sa_column=Column(ARRAY(String)))
```

```python
class Tag(OntoModel):
    id: int
    labels: list[str] = onto_property("schema:keywords")

class TagMap(OntoMapper[Tag]):
    entity = Tag
    id = Map(TagRow.id)
    labels = Map(TagRow.labels, property="schema:keywords")
```

Export emits multiple literal values for list fields.

## Operations

| Topic | Guidance |
|-------|----------|
| Migrations | Alembic (user-owned); OntoSQL does not generate migrations |
| Pooling | SQLAlchemy `create_engine(pool_size=..., max_overflow=...)` |
| Read replicas | Planned for 0.7 — separate engine binding for `find` vs `save` |
| Connection URL | `postgresql+psycopg://user:pass@host/db` (psycopg3) |

## Related

- [Bridge tables](bridge-tables.md) — many-to-many on Postgres
- [Multi-map views](multi-map-views.md) — multiple semantic entities per table
- [ROADMAP](../ROADMAP.md) — 0.7 production Postgres guide
