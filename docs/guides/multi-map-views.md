# Multi-map views

One physical table can back **multiple semantic entities**. Each entity gets its own `OntoModel` and `OntoMapper`; register both mappers on the same session.

## When to use this

- **Vocabulary views** — expose the same row as `schema:Person` and `foaf:Person` with different `@type` and property IRIs.
- **API surfaces** — a public DTO vs an internal rich model over shared storage.
- **Legacy columns** — one mapper omits columns the other maps.

OntoSQL does **not** infer these views. You declare each map explicitly and review them like any other binding.

## Pattern

### Shared physical row

```python
class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str | None = None
```

### Two semantic entities

```python
class SchemaPerson(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"
    id: int
    name: str = onto_property("schema:name")


class FoafPerson(OntoModel):
    type_iri = "foaf:Person"
    iri_template = "https://data.example.org/foaf/{id}"
    id: int
    label: str = onto_property("foaf:name")
```

### Two mappers, same table

```python
class SchemaPersonMap(OntoMapper[SchemaPerson]):
    entity = SchemaPerson
    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")


class FoafPersonMap(OntoMapper[FoafPerson]):
    entity = FoafPerson
    id = Map(PersonRow.id)
    label = Map(PersonRow.name, field="label", property="foaf:name")
```

### Session

```python
with OntoSession(engine, maps=[SchemaPersonMap, FoafPersonMap]) as session:
    schema_view = session.get(SchemaPerson, id=1)
    foaf_view = session.get(FoafPerson, id=1)
```

Both return the same underlying row with different semantic shapes and RDF export metadata.

## FastAPI

Register both entities on `OntoRouter`:

```python
router = OntoRouter(maps=[SchemaPersonMap, FoafPersonMap])
router.register(SchemaPerson)
router.register(FoafPerson)
router.include_in(app)
```

## Rules

- **One mapper per semantic entity type** — the registry rejects duplicate entity registrations.
- **Writes go through one map at a time** — updating via `SchemaPersonMap` changes the shared row; `FoafPerson` reads see the new values.
- **Different `iri_template` values** — export produces distinct `@id` IRIs per view; choose templates deliberately for your graph sync strategy.

## Related

- [Bridge tables](bridge-tables.md) — many-to-many associations
- [Cascade policies](cascade-policies.md) — nested write behavior
- [Architecture](../ARCHITECTURE.md) — explicit mapping rationale
