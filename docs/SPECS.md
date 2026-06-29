# OntoSQL Technical Specification

API contract for **ontosql 0.5.0**. Sections marked *planned* are on the [roadmap](ROADMAP.md).

## Overview

| | |
|---|---|
| PyPI name | `ontosql` |
| Import | `import ontosql` |
| Python | 3.10+ |
| Thesis | Semantic CRUD over SQL via explicit maps |

**ontosql** is a semantic data access layer for Python: Pydantic semantic models, SQLModel physical tables, declarative `OntoMapper` bindings, and `OntoSession` that compiles operations to SQL. JSON-LD, RDF, and FastAPI responses are derived from the same mapping — not from annotating table rows.

See [ARCHITECTURE.md](ARCHITECTURE.md) for layers, glossary, and design rationale. Terms: [GLOSSARY.md](GLOSSARY.md).

## API stability (0.5.x)

| Tier | Import paths | Policy until 1.0 |
|------|----------------|------------------|
| **Beta-stable** | `import ontosql` (root exports), `ontosql.semantic`, `ontosql.mapping`, `ontosql.session`, `ontosql.registry` | Additive changes only in minor releases until 1.0 |
| **Beta-supported** | `ontosql.export`, `ontosql.import_`, `ontosql.sync`, `ontosql.query` | May evolve; documented in [SPECS.md](SPECS.md) |
| **Beta-experimental** | `ontosql.fastapi`, `ontosql.shacl`, `ontosql.export.jsonld` | Extra-gated; may change without deprecation |
| **Internal** | `ontosql.compile`, `ontosql.session._ops`, `_*` helpers | Not part of the public contract — do not import in application code |

**Semver commitment** begins at **1.0** ([ROADMAP.md](ROADMAP.md)). Pre-1.0 releases may rename parameters without a deprecation cycle.

`OntoRouter` is a **supported HTTP scaffold** (beta-experimental) — async-only, with default body limits and semantic validation. **Not safe on public networks** without `dependencies=[Depends(your_auth)]`, rate limits, and object-level authorization ([SECURITY.md](SECURITY.md), [guides/production-router.md](guides/production-router.md)). For hand-written production routes, see [examples/person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py).

## Public API surface

### Root package (`import ontosql`)

| Symbol | Module |
|--------|--------|
| `OntoModel`, `onto_property` | `ontosql.semantic` |
| `Map`, `OntoMapper`, `CascadePolicy` | `ontosql.mapping` |
| `OntoSession`, `AsyncOntoSession`, `Page`, `paginate`, `paginate_async` | `ontosql.session` |
| `GraphSyncError`, `GraphSyncMode` | `ontosql.session` / `ontosql.sync` |
| `GraphSyncFailure` | `ontosql.session` only (not re-exported from root) |
| `OntoImportError` | `ontosql.import_` (also re-exported from root) |
| `PrefixRegistry` | `ontosql.registry` |

`MapperRegistry` is exported from `ontosql.mapping` for multi-map registration; prefer `OntoSession(maps=[...])` for application wiring.

### Supported subpackages

| Package | Key entry points |
|---------|------------------|
| `ontosql.export` | `instance_to_graph`, `instance_to_jsonld`, `instance_to_rdf`, `instances_to_graph`, `instances_to_jsonld`, `instances_to_rdf`, `write_instance_to_graph` |
| `ontosql.import_` | `import_from_jsonld`, `import_from_rdf`, `graph_to_instance`, `OntoImportError` |
| `ontosql.sync` | `push_instance`, `remove_instance`, `StoreSyncTarget`, `GraphSyncTarget`, `GraphSyncMode`, `materialize_find`, `materialize_find_async` |
| `ontosql.query` | `FieldRef`, `FieldPath`, expression operators on semantic fields |
| `ontosql.fastapi` | `OntoRouter`, `DEFAULT_MAX_BODY_BYTES`, `onto_async_session_lifespan`, `AsyncSessionDep`, `get_async_onto_session`, `negotiate_onto_response`, RDF response classes, OpenAPI helpers. `onto_session_lifespan` / `SessionDep` remain for **custom sync routes only** — `OntoRouter` requires async lifespan (requires `ontosql[fastapi]`) |
| `ontosql.shacl` | `shapes_from_mapper`, `validate_instance` (requires `ontosql[shacl]`) |

### Instance methods on `OntoModel`

- `to_jsonld()`, `to_rdf()` — export via TripleModel
- `from_jsonld(doc, mapper=...)` — import via mapper metadata

### Internal (unsupported)

- `ontosql.compile.*` — SQL plan types and executors; the `ontosql.compile` package has an empty `__all__` and is not re-exported
- `ontosql.session._ops` — shared session helpers

## Implementation phases

| Phase | Scope |
|-------|--------|
| **0.2.0** | Mapper registry, `get` / `find`, semantic filters, `PrefixRegistry` |
| **0.2.x** | Export (`to_jsonld` / `to_rdf`); export polish via TripleModel APIs |
| **0.3.0** | `save` / `delete`, cascade policies, partial updates, `OntoRouter`, OpenAPI |
| **0.4.0** | RDF import, graph sync, SHACL, `REPLACE` cascade, prefix bundles |
| **0.5.0** | `Map.computed`, `Map.collection`, batch export, select-plan cache, dialect guides |
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

Pass a `PrefixRegistry` to export/import helpers or use `PrefixRegistry.curated()` — there is no class-level registry on `OntoModel`.

### `onto_property`

Field helper attaching ontology metadata to semantic fields.

| Key | Description |
|-----|-------------|
| `property` | Property CURIE or IRI (positional arg) |
| `datatype` | XSD or other datatype IRI |
| `iri` | Explicit property IRI override |
| `language` | Language tag for literals |

Named graph export is planned via TripleModel — see [ROADMAP.md](ROADMAP.md).

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
| `Map.computed(expr, field=..., property=...)` | Read-only semantic field from SQL expression (0.5.0) |
| `Map.collection(...)` | Many-to-many via bridge table (0.5.0) |

### `Map.computed` (0.5.0)

Read-only fields compiled into `SELECT` projections. Excluded from `save()`; raises `WriteCompileError` if a computed field appears in a partial update.

### `Map.collection` (0.5.0)

Many-to-many lists via a bridge table. Loaded with batched queries after `find` / `get` (not joined into the root SELECT). Cascade policies: `link`, `upsert`, `replace`, `ignore`. See [bridge-tables.md](guides/bridge-tables.md).

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
    person = session.get(Person, identity=1)
```

Sync `OntoSession` **must** be used as a context manager (SQLAlchemy session opens in `__enter__`).

```python
async with AsyncOntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
    person = await session.get(Person, identity=1)
```

| Method | Status | Description |
|--------|--------|-------------|
| `get(entity, *, identity=..., iri=...)` | 0.2.0 | Load one instance by primary key or IRI |
| `find(entity, *, where=..., order_by=..., limit=..., offset=...)` | 0.2.0 | Query with semantic field expressions |
| `save(instance, *, flush_now=True)` | 0.3.0 | Insert or update; returns hydrated instance |
| `delete(instance, *, flush_now=True)` | 0.3.0 | Delete root row; `REPLACE` nested/collection members when exclusively owned |
| `flush()` / `clear_pending()` | 0.3.0 | Apply or discard pending write queue |
| `rollback()` (sync) | 0.5.x | Roll back open SQLAlchemy transaction |
| `count(entity, *, where=...)` | 0.3.0 | Count rows matching a filter; subtracts pending-delete tombstones in-session |
| `paginate(...)` / `paginate_async(...)` | 0.3.0 | `Page` with optional total count |
| `retry_graph_sync()` | 0.5.x | Retry queued graph ops after partial post-commit failure |
| `graph_sync_pending` / `graph_sync_failures` | 0.5.x | Graph split-brain diagnostics |

Optional constructor arguments (0.4.0):

- `graph_sync` — `GraphSyncTarget` or `Store` with `graph` and `update_graph(add=, remove=)`
- `graph_sync_mode` — `GraphSyncMode`: `"patch"` (default), `"replace"`, or `"add"`

Graph sync is applied **after SQL commit** on session exit. Rolled-back sessions discard queued graph updates. Partial graph failures raise `GraphSyncError` with remaining queue preserved for `retry_graph_sync()`. `flush()` queues graph sync for flushed writes; commit still required before the graph updates.

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

Module-level helpers: `ontosql.export.instance_to_jsonld`, `instance_to_rdf`, `instance_to_graph`, `instances_to_jsonld`, `instances_to_rdf`, `instances_to_graph` (0.5.0 batch).

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
restored = import_from_rdf(turtle_bytes, PersonMap, format="turtle", max_bytes=1_000_000, max_triples=10_000)
```

```python
person = Person.from_jsonld(doc, mapper=PersonMap)
```

Hydration uses **mapper metadata** (`Map.property`, `Map.nested`, `type_iri`, `iri_template`). Raises `OntoImportError` on type mismatch or ambiguous subjects. Optional `max_bytes` / `max_triples` guard untrusted RDF payloads.

---

## Graph sync (0.4.0)

Module: `ontosql.sync`

```python
from ontosql.sync import push_instance, remove_instance, StoreSyncTarget
from ontosql.sync.graph import sync_instance_to_store
from ontosql.sync.materialize import materialize_find
```

| API | Description |
|-----|-------------|
| `push_instance(instance, target, *, mapper, mode="patch")` | Push instance subgraph to a `Store` or `GraphSyncTarget` |
| `remove_instance(instance, target, *, mapper)` | Remove instance subgraph from a graph target |
| `sync_instance_to_store(instance, store, *, mode, mapper_cls)` | Lower-level; mutates a `Store` in place (requires `mapper_cls`) |
| `StoreSyncTarget` | In-memory target wrapping a `Store` |
| `materialize_find(session, entity_type, ...)` | Merge sync `find()` results into one `Store` |
| `materialize_find_async(session, entity_type, ...)` | Merge async `find()` results into one `Store` |

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

### OntoRouter (0.5.x)

`OntoRouter` uses **`AsyncSessionDep`** on all routes. Wire **`onto_async_session_lifespan(app, engine, maps)`** at startup (async engine required).

| Option | Default (0.5+) | Detail |
|--------|------------------|--------|
| `validate_entities` | `True` | Runs `OntoModel.model_validate` on create/patch |
| `max_body_bytes` | `65536` | POST/PATCH body cap (413 when exceeded) |
| `dependencies` | `[]` | **Required for internet** — FastAPI `Depends` authn/authz on every route |

| Gap | Detail |
|-----|--------|
| No built-in auth | Pass `dependencies=[Depends(your_auth)]` |
| No rate limiting | Add middleware or reverse-proxy limits |
| List `limit` | Capped at 100; runs find + count per list request |
| Graph sync | Not wired by default; hybrid apps see [HYBRID.md](HYBRID.md) |

List JSON-LD uses `instances_to_jsonld()`. Optional class attribute **`jsonld_context`** (or `context` for OpenAPI) overrides `@context` on list responses.

**Custom sync routes:** `onto_session_lifespan` + `SessionDep` for blocking SQLAlchemy in hand-written handlers — not used by `OntoRouter`.

Before production: auth dependencies, rate limits, `debug=False`, protect `/docs`. See [SECURITY.md](SECURITY.md) and [guides/production-router.md](guides/production-router.md).

---

## Package layout

```text
src/ontosql/
  __init__.py
  semantic/       # OntoModel, onto_property
  mapping/        # OntoMapper, Map, registry
  compile/        # SQLAlchemy expression builders + write plans + cache + collection
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

## Naming conventions

| Concept | Preferred name | Notes |
|---------|----------------|-------|
| Primary key lookup | `identity=` | `session.get(Person, identity=1)` — not `id=` |
| HTTP path param | `entity_id` | FastAPI route param; maps to `identity=` |
| Mapper class arg | `mapper_cls` | Low-level sync (`sync_instance_to_store`) |
| Mapper class arg | `mapper` | User-facing import (`import_from_rdf`, `from_jsonld`) |
| RDF import module | `ontosql.import_` | Trailing underscore avoids `import` keyword |
| JSON-LD list context | `jsonld_context` | Optional `ClassVar` on `OntoModel`; OpenAPI also reads `context` |
| Graph sync mode | `GraphSyncMode` | Literals `"patch"`, `"replace"`, `"add"` |

## Related documents

- [ECOSYSTEM.md](ECOSYSTEM.md)
- [HYBRID.md](HYBRID.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [DEPS.md](DEPS.md)
