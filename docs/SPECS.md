# OntoSQL Technical Specification

API contract for **ontosql 0.2.0**. Sections marked *planned* are on the [roadmap](ROADMAP.md).

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
| **0.3** | `save` / `delete`, cascade policies, partial updates, `OntoRouter`, OpenAPI |
| **0.4** | RDF import, graph sync (`ontosql[sparql]`), SHACL from maps |
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

### Cascade policies (write path — *planned* 0.2.x / 0.3)

Nested `save` behavior is **explicit** on `Map.nested`:

| Policy | Behavior |
|--------|----------|
| `link` | Update FK only; nested row must exist |
| `upsert` | Insert or update nested entity |
| `replace` | Replace nested association |
| `ignore` | Do not persist nested changes |

Default for new maps: `link` (fail closed on ambiguous graphs).

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
| `save(instance)` | planned | Insert or update; returns hydrated instance |
| `delete(instance)` | planned | Delete per map delete plan |
| `execute_sql(...)` | 0.2.0 | Escape hatch for raw SQL |

- Transactions: one transaction per context manager; rollback on exception.
- Identity map for repeated `get` in one session *(planned)*.

### Query expressions

Filters reference **semantic** attributes; the session compiles joins from the mapper.

```python
session.find(Person, where=Person.name.startswith("A"), limit=20)
```

Supported operators (0.2.0): comparisons, `startswith`, `in_`, `is_null`, boolean `&` / `|`. Unsupported expressions raise at compile time.

---

## `PrefixRegistry`

CURIE and JSON-LD context utilities backed by semantic/map metadata:

- CURIE `expand` — delegates to TripleModel `expand_curie()` for `prefix:local` terms
- CURIE `compact` — longest-prefix match (OntoSQL-local)
- JSON-LD `@context` via `context_dict()`
- Copy-on-write `with_prefix`, `freeze()`

Used by session (IRI resolution), export, and FastAPI responses.

---

## Export (0.2.x)

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

### Optional SparqlModel integration (`ontosql[sparql]`)

For graph sync and hybrid architectures, SparqlModel provides `SPARQLSession` and SPARQL query compilation over the same TripleModel graph engine. See [ECOSYSTEM.md](ECOSYSTEM.md).

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

**0.3:** `OntoRouter` for CRUD routes; OpenAPI semantic enrichment.

---

## Package layout

```text
src/ontosql/
  __init__.py
  semantic/       # OntoModel, onto_property
  mapping/        # OntoMapper, Map, registry
  compile/        # SQLAlchemy expression builders
  session/        # OntoSession, AsyncOntoSession
  query/          # semantic expressions
  export/         # instance export (TripleModel) + format helpers
  registry.py     # PrefixRegistry
  fastapi/
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
- Standards compliance for **export** (JSON-LD, RDF); SHACL validation planned
- Progressive enhancement via optional extras (`fastapi`, future `shacl`, `jsonld`)

## Related documents

- [ECOSYSTEM.md](ECOSYSTEM.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](ROADMAP.md)
- [DEPS.md](DEPS.md)
