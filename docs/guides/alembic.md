# Alembic and schema migrations

OntoSQL **does not generate or run database migrations**. You own the physical schema with Alembic (or your migration tool). OntoSQL compiles CRUD against SQLModel tables that must match your live database.

## Two layers to keep in sync

| Layer | Tool | Changes when |
|-------|------|--------------|
| **Physical** | SQLModel + Alembic | Columns, tables, FKs, indexes |
| **Semantic** | `OntoModel` | Application shape, validation |
| **Mapping** | `OntoMapper` | Field → column bindings |

When you add a column in Alembic, update the SQLModel row class **and** the `Map(...)` binding if the field is exposed semantically.

## Typical workflow

### 1. Change SQLModel row model

```python
class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str | None = None  # new column
```

### 2. Generate Alembic revision

```bash
alembic revision --autogenerate -m "add people.email"
alembic upgrade head
```

Use your existing Alembic + SQLModel metadata setup (`SQLModel.metadata` as `target_metadata`).

### 3. Update semantic model (if exposed)

```python
class Person(OntoModel):
    ...
    email: str | None = onto_property("schema:email")
```

### 4. Update mapper

```python
class PersonMap(OntoMapper[Person]):
    ...
    email = Map(PersonRow.email, property="schema:email")
```

### 5. Test

Run integration tests against a migrated database. See [testing guide](testing.md).

## Operations that need extra care

| Change | OntoSQL impact |
|--------|------------------|
| **Rename column** | Update `Map` column reference; semantic field name can stay stable |
| **Split table** | New row model + join in `Map.nested` or bridge — no auto-migration |
| **Drop column** | Remove from mapper before drop, or `save()` may fail |
| **FK change** | Review nested `cascade` policy — especially `REPLACE` |
| **NOT NULL without default** | Backfill in Alembic before enforcing |

## Semantic-only fields

`Map.computed` and read-only semantic fields **do not** require Alembic columns. Do not add Alembic migrations for computed-only fields.

## OntoSQL does not migrate

- No `alembic revision` integration
- No diff from `OntoMapper` to SQL DDL
- No automatic detection of schema drift at runtime

Planned [mapper lint](../ROADMAP.md) (0.6) may catch orphan maps at import time — not shipped yet.

## Postgres notes

UUID, JSONB, ARRAY patterns: [postgres-dialect.md](postgres-dialect.md).

## Related

- [FAQ](../FAQ.md) — who owns migrations
- [ARCHITECTURE.md](../ARCHITECTURE.md) — physical vs semantic layers
- [enterprise adoption](../enterprise-adoption.md)
