# OntoSQL Technical Specification

API contract for **ontosql 0.4.0**. Sections marked *planned* are on the [roadmap](ROADMAP.md).

## Overview

| | |
|---|---|
| PyPI name | `ontosql` |
| Import | `import ontosql` |
| Python | 3.10+ |
| Thesis | Semantic CRUD over SQL via explicit maps |

**ontosql** is a semantic data access layer for Python: Pydantic semantic models, SQLModel physical tables, declarative `OntoMapper` bindings, and `OntoSession` that compiles operations to SQL. JSON-LD, RDF, and FastAPI responses are derived from the same mapping — not from annotating table rows.

See [ARCHITECTURE.md](ARCHITECTURE.md) for layers, glossary, and design rationale.

## Implementation phases

| Phase | Scope |
|-------|--------|
| **0.2.0** | Mapper registry, `get` / `find`, semantic filters, `PrefixRegistry` |
| **0.2.x** | Export (`to_jsonld` / `to_rdf`); export polish via TripleModel APIs |
| **0.3.0** | `save` / `delete`, cascade policies, partial updates, `OntoRouter`, OpenAPI |
| **0.4.0** | RDF import, graph sync, SHACL, `REPLACE` cascade, prefix bundles |
| **0.5** | Advanced mapper patterns, batch export, dialect / performance |
| **0.6** | Aggregations, extended filters, `explain`, mapper lint |
| **0.7** | Bulk write, observability, read-replica routing, production guides |
| **0.8** | Schema packs, OWL codegen, vocabulary modules |
| **0.9** | API freeze, contract tests, docs site, RC releases |
| **1.0** | Semver guarantee, GA, support policy |

---

## Semantic models

### `OntoModel`

Base class for semantic entities (Pydantic v2).

```python
class Person(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"

    id: int
    name: str = onto_property("schema:name")
    employer: Organization | None = onto_property("schema:worksFor")
```

Class attributes:

| Attribute | Description |
|-----------|-------------|
| `type_iri` | RDF class CURIE or IRI (`@type`) |
| `iri_template` | Instance `@id` template; `{field}` placeholders from semantic fields |
| `registry` | Optional class-level `PrefixRegistry` override |

### `onto_property`

Field helper attaching ontology metadata to semantic fields.

| Key | Description |
|-----|-------------|
| `property` | Property CURIE or IRI (positional arg) |
| `datatype` | XSD or other datatype IRI |
| `iri` | Explicit property IRI override |
| `language` | Language tag for literals |
| `graph` | Named graph IRI (export) |

---

## Physical models

SQLModel classes with `table=True` mirror the database. They are **not** semantic entities.

```python
class PersonRow(SQLModel, table=True):
    __tablename__ = "people"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    org_id: int | None = Field(default=None, foreign_key="orgs.id")
```

- Migrations remain user-owned (Alembic, etc.).
- Unmapped columns are never touched by semantic CRUD unless bound in a map.

---

## Mapping

### `OntoMapper`

Declares how a semantic entity maps to SQL.

```python
class PersonMap(OntoMapper[Person]):
    entity = Person

    id = Map(PersonRow.id)
    name = Map(PersonRow.name, property="schema:name")
    employer = Map.nested(
        Organization,
        join=(PersonRow.org_id == OrgRow.id),
        target=OrgRow,
        nested_map=OrganizationMap,
        property="schema:worksFor",
    )
```

### `Map` bindings

| Binding | Use |
|---------|-----|
| `Map(column)` | Direct column |
| `Map(expr, property=...)` | SQLAlchemy column element |
| `Map.nested(...)` | Join + nested semantic type via another mapper |
| `Map.computed(...)` | Read-only semantic field from SQL expression *(planned)* |

### Cascade policies (write path — 0.3.0)

Nested `save` behavior is **explicit** on `Map.nested`:

| Policy | Behavior |
|--------|----------|
| `link` | Update FK only; nested row must exist |
| `upsert` | Insert or update nested entity |
| `replace` | On update: delete old nested row when FK changes or nested becomes `None`; then upsert new nested (0.4.0) |
| `ignore` | Do not persist nested changes |

Default for new maps: `link` (fail closed on ambiguous graphs).

> **REPLACE note:** Deletes the previous nested entity referenced by the session snapshot when the association changes. Do not use `REPLACE` for nested rows shared across multiple parents — use `LINK` or `IGNORE`.

### Registry

- Register mappers with `OntoSession(maps=[...])` or `AsyncOntoSession(maps=[...])`.
- One physical table may have multiple mappers.
- One mapper per semantic entity type.

---

## Session

### `OntoSession` / `AsyncOntoSession`

Unit of work bound to a SQLAlchemy/SQLModel engine.

```python
with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    person = session.get(Person, id=1)
```

```python
async with AsyncOntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    person = await session.get(Person, id=1)
```

| Method | Status | Description |
|--------|--------|-------------|
| `get(entity, *, id=..., iri=...)` | 0.2.0 | Load one instance by primary key or IRI |
| `find(entity, *, where=..., order_by=..., limit=..., offset=...)` | 0.2.0 | Query with semantic field expressions |
| `save(instance)` | 0.3.0 | Insert or update; returns hydrated instance |
| `delete(instance)` | 0.3.0 | Delete root row by identity |
| `flush()` / `rollback_pending()` | 0.3.0 | Pending write queue |
| `count(entity, *, where=...)` | 0.3.0 | Count rows matching a filter |
| `paginate(...)` | 0.3.0 | `Page` with optional total count |
| `execute_sql(...)` | 0.2.0 | Escape hatch for raw SQL |

Optional constructor arguments (0.4.0):

- `graph_sync` — target with `graph` and `update_graph(add=, remove=)`; pushes after `save()`
- `graph_sync_mode` — `"patch"` (default), `"replace"`, or `"add"`

- Transactions: one transaction per context manager; rollback on exception.
- Identity map for repeated `get` in one session (0.3.0).

### Query expressions

Filters reference **semantic** attributes; the session compiles joins from the mapper.

```python
session.find(Person, where=Person.name.startswith("A"), limit=20)
```

Supported operators: comparisons, `startswith`, `contains`, `endswith`, `in_`, `is_null`, boolean `&` / `|`. Nested `FieldPath` filters and `OrderBy(desc=)` (0.3.0). Unsupported expressions raise at compile time.

---

## `PrefixRegistry`

CURIE and JSON-LD context utilities backed by semantic/map metadata:

- CURIE `expand` — delegates to TripleModel `expand_curie()` for `prefix:local` terms
- CURIE `compact` — longest-prefix match (OntoSQL-local)
- JSON-LD `@context` via `context_dict()`
- Copy-on-write `with_prefix`, `freeze()`
- `PrefixRegistry.curated(bundle)` — `"schema_org"` or `"dcterms"` vocabulary bundles (0.4.0)

Used by session (IRI resolution), export, import, sync, and FastAPI responses.

---

## Export (0.2.x+)

Export operates on **semantic instances** using `type_iri`, `onto_property`, and IRI templates. Implementation builds a TripleModel `Store` graph and serializes with pyoxigraph.

```python
person.to_jsonld(registry=None) -> dict
person.to_rdf(format="turtle", registry=None) -> str
```

Module-level helpers: `ontosql.export.instance_to_jsonld`, `instance_to_rdf`, `instance_to_graph`.

| Format | Notes |
|--------|--------|
| JSON-LD | `@context` from `PrefixRegistry`; `@id`, `@type`, nested object links |
| Turtle, N-Triples, RDF/XML | Via TripleModel `Store.serialize()` |
| Nested entities | Recursively exported; object properties link by instance IRI |

TripleModel remains an implementation detail for most apps; users call `to_jsonld()` / `to_rdf()` on semantic instances.

Export honors `onto_property(datatype=..., language=...)` on literals (0.4.0).

---

## Import (0.4.0)

Module: `ontosql.import_` (note trailing underscore — `import` is a Python keyword).

```python
from ontosql.import_ import import_from_jsonld, import_from_rdf, graph_to_instance

restored = import_from_jsonld(doc, PersonMap)
restored = import_from_rdf(turtle_bytes, PersonMap, format="turtle")
```

```python
person = Person.from_jsonld(doc, mapper=PersonMap)
```

Hydration uses **mapper metadata** (`Map.property`, `Map.nested`, `type_iri`, `iri_template`). Raises `OntoImportError` on type mismatch or ambiguous subjects.

---

## Graph sync (0.4.0)

Module: `ontosql.sync`

```python
from ontosql.sync import push_instance, StoreSyncTarget, replace_subject, patch_subject
from ontosql.sync.graph import sync_instance_to_store
from ontosql.sync.materialize import materialize_find, materialize_entity
```

| API | Description |
|-----|-------------|
| `push_instance(instance, target, *, mode="patch")` | Push instance subgraph to a `Store` or `GraphSyncTarget` |
| `sync_instance_to_store(instance, store, *, mode, mapper_cls)` | Lower-level; mutates a `Store` in place |
| `StoreSyncTarget` | In-memory target wrapping a `Store` |
| `materialize_find(session, entity_type, ...)` | Merge `find()` results into one `Store` |
| `materialize_entity(instance)` | Single-instance graph |

Modes: `add` (append), `replace` (remove subject triples then add), `patch` (owned-predicate diff).

### SparqlModel adapter (`ontosql[sparql]`)

```python
from ontosql.sync.sparql import OntoGraphSync

sync = OntoGraphSync(sparql_session, maps=[PersonMap], mode="patch")
sync.push(person)
restored = sync.pull(Person, iri="https://data.example.org/person/1")
```

See [HYBRID.md](HYBRID.md) for deployment patterns.

---

## SHACL (0.4.0, `ontosql[shacl]`)

Module: `ontosql.shacl`

```python
from ontosql.shacl import shapes_from_mapper, shapes_from_mappers, validate_instance

shapes = shapes_from_mapper(PersonMap)
report = validate_instance(person, PersonMap)  # report.conforms, report.message
```

Generates `sh:NodeShape` / `sh:PropertyShape` from `OntoMapper` and field types. Validation uses pySHACL.

---

## FastAPI (`ontosql[fastapi]`)

```python
from ontosql.fastapi import negotiate_onto_response

return negotiate_onto_response(request, semantic_instance)
```

| MIME type | Response |
|-----------|----------|
| `application/ld+json` | JSON-LD |
| `text/turtle` | Turtle |
| `application/n-triples` | N-Triples |
| `application/rdf+xml` | RDF/XML |

- RFC 7231-style `Accept` parsing (`q`, `charset`, `q=0` rejection).
- `orjson` for JSON-LD bodies when installed.

**0.3.0:** `OntoRouter` for CRUD routes; `onto_session_lifespan`; OpenAPI semantic enrichment.

### OntoRouter production limitations (0.3.x)

`OntoRouter` is **demo-grade**, not production-hardened:

| Gap | Detail |
|-----|--------|
| No auth | All CRUD routes are unauthenticated unless the host app adds middleware or dependencies |
| No body validation | POST/PATCH handlers use `model_construct` / raw JSON — no Pydantic `model_validate` |
| Sync session in async handlers | Blocking I/O under load; use `AsyncOntoSession` with app-level wiring |
| List `limit` | Capped at 100 (0.3.1+); still runs find + count per list request |

Before production: wire auth dependencies, validate bodies with generated Pydantic models, and restrict mount paths.

---

## Package layout

```text
src/ontosql/
  __init__.py
  semantic/       # OntoModel, onto_property
  mapping/        # OntoMapper, Map, registry
  compile/        # SQLAlchemy expression builders + write plans
  session/        # OntoSession, AsyncOntoSession, pagination
  query/          # semantic expressions, FieldPath
  export/         # instance export (TripleModel) + jsonld helpers
  import_/        # RDF import into OntoModel (0.4.0)
  sync/           # graph sync, materialize, SparqlModel adapter (0.4.0)
  shacl/          # shape generation + validation (0.4.0)
  registry.py     # PrefixRegistry
  fastapi/
    deps.py
    router.py
    openapi.py
    negotiate.py
    responses.py
```

---

## Anti-patterns

Do **not**:

- Use `table=True` on semantic `OntoModel` classes
- Assume one SQL table per ontology class
- Call `to_jsonld()` on SQLModel row instances without a session/map
- Map two semantic fields to the same property without a documented resolution rule
- Rely on automatic join inference without an explicit `Map.nested`

---

## Design principles

- Pythonic models first — semantic types are what you import in app code
- Explicit over magical — maps are reviewable data
- SQL is compiled, not hand-written for the happy path
- Standards compliance for **export** and **import** (JSON-LD, RDF); SHACL validation via `ontosql[shacl]`
- Progressive enhancement via optional extras (`fastapi`, `shacl`, `jsonld`, `sparql`)

## Related documents

- [ECOSYSTEM.md](ECOSYSTEM.md)
- [HYBRID.md](HYBRID.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [DEPS.md](DEPS.md)
