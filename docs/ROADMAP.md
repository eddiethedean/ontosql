# OntoSQL Roadmap

This document describes planned releases for **ontosql**. For the API contract, see [SPECS.md](SPECS.md). For dependency choices, see [DEPS.md](DEPS.md). For architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Vision

OntoSQL is the **operational semantic layer** for Python apps on SQL: define relational schemas with SQLModel, define application concepts with Pydantic semantic models, connect them with explicit maps, and get CRUD plus JSON-LD/RDF/FastAPI from one source of truth.

OntoSQL shares RDF infrastructure with [TripleModel](https://github.com/eddiethedean/triplemodel) and aligns with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) for graph-native workloads — see [ECOSYSTEM.md](ECOSYSTEM.md).

## Shipped (0.4.0)

| Area | Status |
|------|--------|
| RDF import (`ontosql.import_`) | Shipped |
| Graph sync (`ontosql.sync`) + session `graph_sync` hook | Shipped |
| `OntoGraphSync` SparqlModel adapter (`ontosql[sparql]`) | Shipped |
| Materialized graph views (`materialize_find`, `materialize_find_async`) | Shipped |
| SHACL generation + validation (`ontosql[shacl]`) | Shipped |
| `CascadePolicy.REPLACE` distinct semantics | Shipped |
| `PrefixRegistry.curated()` bundles | Shipped |
| Export literal `datatype` / `language` | Shipped |
| [HYBRID.md](HYBRID.md) deployment guide | Shipped |

---

## Shipped (0.3.1)

| Area | Status |
|------|--------|
| PyPI release workflow on semver tags | Shipped |
| Delete plan safety (`ExecuteError` without `where`) | Shipped |
| Behavioral integration test refactor | Shipped |

---

## Shipped (0.3.0)

| Area | Status |
|------|--------|
| `OntoModel`, `onto_property` | Shipped |
| `OntoMapper`, `Map`, `Map.nested`, `CascadePolicy`, `fk_column` | Shipped |
| `OntoSession` / `AsyncOntoSession` `get` / `find` / `save` / `delete` | Shipped |
| Identity map, `flush`, `clear_pending`, partial updates | Shipped |
| Semantic query expressions, nested `FieldPath`, `paginate` | Shipped |
| `PrefixRegistry` | Shipped (CURIE expand via TripleModel) |
| Export (`to_jsonld`, `to_rdf`) | Shipped (TripleModel serializers) |
| `ontosql.export` module | Shipped |
| TripleModel core dependency | Shipped |
| `ontosql[fastapi]` content negotiation + `OntoRouter` | Shipped |
| `ontosql[jsonld]` optional extra | Shipped |
| `ontosql[sparql]` extra (dependency pin) | Shipped |
| [ECOSYSTEM.md](ECOSYSTEM.md) | Shipped |

---

## v0.2.x — Export polish (patch releases)

**Theme:** Harden RDF export before the write path lands.

### Planned

- **Literal typing** — honor `onto_property(datatype=..., language=...)` via TripleModel coercion when available
- **Collection shapes** — `set` vs RDF `list` encoding (blocked on [TripleModel #18](https://github.com/eddiethedean/triplemodel/issues/18))
- **Named graphs** — honor `onto_property(..., graph=...)` on export (blocked on [TripleModel #19](https://github.com/eddiethedean/triplemodel/issues/19))
- **JSON-LD documents** — adopt `graph_to_jsonld_document` when TripleModel ships it ([#15](https://github.com/eddiethedean/triplemodel/issues/15))
- **Prefix unification** — migrate `PrefixRegistry` to TripleModel `PrefixMap` when available ([#13](https://github.com/eddiethedean/triplemodel/issues/13))
- **Export refactor** — delegate instance→graph to TripleModel annotated export protocol ([#12](https://github.com/eddiethedean/triplemodel/issues/12))

### Success criteria

- Person / Organization nested export round-trips with correct XSD types and language tags
- No direct `pyoxigraph` imports in OntoSQL once TripleModel term builders land ([#16](https://github.com/eddiethedean/triplemodel/issues/16))

---

## v0.3 — Write path and API layer (shipped in 0.3.0)

**Theme:** Full CRUD over SQL and production FastAPI wiring.

### Shipped

- **`save(instance)`** — insert/update plans across mapped tables; transaction boundaries
- **`delete(instance)`** — delete plans per mapper; root + nested ownership rules
- **Nested cascade policies** — explicit `link`, `upsert`, `replace`, `ignore` on `Map.nested` (never inferred)
- **Partial updates** — `model_dump(exclude_unset=True)` drives PATCH-style SQL
- **Identity map** — repeated `get` returns same in-session instance
- **`flush` / `rollback`** — pending write queue (mirror SparqlModel session ergonomics)

#### Query and API

- **`find` enhancements** — `order_by` on nested fields; additional filter operators as needed
- **Bulk `find`** — pagination helpers (`limit` / `offset` / cursor); list endpoints
- **`OntoRouter`** — auto-register CRUD routes from mappers
- **OpenAPI enrichment** — ontology IRIs, semantic media types, `@context` hints in schema docs
- **FastAPI** — session dependency helpers; negotiated responses wired to `to_jsonld()` / `to_rdf()` by default

#### Extras

- **`ontosql[jsonld]`** — PyLD compaction and framing, or thin wrapper over `triplemodel[jsonld]` ([#25](https://github.com/eddiethedean/triplemodel/issues/25))

### Dependencies on TripleModel

| OntoSQL feature | TripleModel prerequisite |
|-----------------|------------------------|
| Richer export in write responses | [#12](https://github.com/eddiethedean/triplemodel/issues/12) annotated export, [#14](https://github.com/eddiethedean/triplemodel/issues/14) literal coercion |
| Stable cross-store IRIs | [#17](https://github.com/eddiethedean/triplemodel/issues/17) subject IRI templates |
| Compact JSON-LD API bodies | [#15](https://github.com/eddiethedean/triplemodel/issues/15), [#25](https://github.com/eddiethedean/triplemodel/issues/25) |

### Success criteria

- Round-trip: create → read → update nested association → delete
- Demo app: full CRUD + content negotiation in under ~30 lines of wiring
- Write path covered by integration tests (sync + async) on SQLite and Postgres

---

---

## v0.4 — Validation and graph interoperability (shipped in 0.4.0)

**Theme:** Close the loop between SQL operational stores and RDF graphs.

### Shipped

- **RDF import** — `import_from_jsonld`, `import_from_rdf`, `graph_to_instance` via mapper metadata
- **Graph sync** — `push_instance`, `sync_instance_to_store`, `OntoSession(graph_sync=...)`
- **SparqlModel adapter** — `OntoGraphSync` push/pull (`ontosql[sparql]`)
- **Materialized views** — `materialize_find`, `materialize_find_async`
- **SHACL** — `shapes_from_mapper`, `validate_instance` (`ontosql[shacl]`)
- **Prefix bundles** — `PrefixRegistry.curated("schema_org" | "dcterms")`
- **`CascadePolicy.REPLACE`** — delete old nested row on association change

### Success criteria (met)

- Export → import preserves `@id`, `@type`, and mapped properties for Person / Organization
- `OntoSession.save()` can push to an in-memory `SPARQLSession` with matching IRIs
- SHACL shapes validate graphs produced by session + export

---

## Release ladder (0.5 → 1.0)

| Version | Theme | Outcome |
|---------|--------|---------|
| **0.5** | Advanced maps & scale | Complex schemas and throughput |
| **0.6** | Query power & DX | Richer reads and easier debugging |
| **0.7** | Production operations | Observable, deployable services |
| **0.8** | Vocabulary & codegen | Reusable schema packs and stubs |
| **0.9** | Release candidate | API freeze, docs site, reference apps |
| **1.0** | Stable platform | Semver commitment and GA |

---

## Shipped (0.5.0)

| Area | Status |
|------|--------|
| `Map.computed` — read-only SQL expressions | Shipped |
| `Map.collection` — bridge-table many-to-many with cascade policies | Shipped |
| Multi-map views — docs + example (`multi-map-views.md`) | Shipped |
| Batch export — `instances_to_graph` / `instances_to_jsonld` / `instances_to_rdf` | Shipped |
| Select-plan skeleton cache (`compile/cache.py`) | Shipped |
| Batched collection hydration (N+1 avoidance) | Shipped |
| Postgres dialect guide (`postgres-dialect.md`) | Shipped |

### Success criteria (met)

- Documented patterns for bridge tables and polymorphic semantic views
- Batch export of 1k+ instances uses a single `Store` allocation
- Collection `find` uses one root SELECT + one batched collection query per field

---

## v0.5 — Mapper ergonomics and scale (shipped in 0.5.0)

**Theme:** Advanced mapping patterns for real-world schemas.

### Shipped

- **`Map.computed`** — read-only semantic fields from SQL expressions
- **Multi-map views** — one table → multiple semantic entities (`schema:Person` vs `foaf:Person`)
- **Bridge / join tables** — `Map.collection` many-to-many mapper patterns
- **Batch export** — `instances_to_graph` and batch helpers for `find` result sets
- **Dialect notes** — Postgres JSON, UUID, array columns in maps (`postgres-dialect.md`)
- **Performance** — compiled plan caching; N+1 avoidance on collection `find`

### Success criteria (met)

- Documented patterns for bridge tables and polymorphic semantic views
- Batch export of 1k+ instances without per-row graph allocation hotspots

---

## v0.6 — Query power and developer experience

**Theme:** Richer read paths and tooling that makes maps debuggable.

### Planned

#### Query extensions

- **Aggregations** — `count`, `min`, `max`, `sum` over semantic fields where mappable to SQL
- **`group_by`** — semantic grouping compiled to SQL `GROUP BY`
- **Additional filters** — `contains`, `endswith`, `between`, `not_` / negation patterns
- **`distinct` / `exists`** — subquery-friendly semantic expressions
- **Eager-load depth** — control nested hydration depth on `get` / `find` (mirror SparqlModel `depth=`)

#### Developer experience

- **`session.explain(find(...))`** — compiled SQL + join plan for debugging
- **Mapper lint** — validate maps at import time (orphan columns, duplicate predicates, impossible joins)
- **Clear compile errors** — field-level messages when a query cannot be compiled
- **REPL-friendly helpers** — pretty-print plans and hydrated instances in notebooks

### Success criteria

- Representative analytics query (`count` persons per organization) compiles without raw SQL
- Mapper misconfiguration fails at class definition or session init with actionable errors

---

## v0.7 — Production operations

**Theme:** Run OntoSQL-backed APIs and workers in production with confidence.

### Planned

#### Session and database operations

- **Bulk write** — `save_all`, `delete_all` with batched SQL
- **Upsert maps** — dialect-specific `ON CONFLICT` / `MERGE` policies on `Map`
- **Read/write routing** — optional read-replica engine binding for `find` vs `save`
- **Savepoints** — nested transaction boundaries for partial rollback

#### Observability and deployment

- **Structured logging** — compile and execute events with entity type, mapper, timing
- **OpenTelemetry hooks** — spans around compile, hydrate, export (optional `ontosql[otel]` extra)
- **FastAPI lifespan recipes** — engine pool sizing, graceful shutdown, health endpoints
- **Postgres integration guide** — connection pooling, JSONB maps, advisory locks

### Success criteria

- Reference FastAPI app exposes `/health` and emits trace spans for `get` / `save`
- Bulk upsert of 10k rows completes with documented batch-size guidance

---

## v0.8 — Vocabulary packs and codegen

**Theme:** Ship reusable ontology modules instead of every team defining schema.org from scratch.

### Planned

- **Schema packs** — `ontosql.vocab.schema_org`, `dcterms`, `skos` (aligned with TripleModel [#24](https://github.com/eddiethedean/triplemodel/issues/24))
- **Pack contents** — `PrefixRegistry` defaults, example `OntoModel` stubs, sample `OntoMapper` templates
- **OWL / RDFS codegen** — generate `OntoModel` + mapper skeletons from ontology files (via TripleModel codegen)
- **`register_model_exporter` integration** — adopt TripleModel adapter registry ([#22](https://github.com/eddiethedean/triplemodel/issues/22)) for third-party packs
- **Pack publishing guide** — how to ship domain vocabularies as optional `ontosql-*` packages

### Success criteria

- `pip install ontosql[schema]` (or companion package) provides working schema.org Person/Organization models
- Codegen from a small OWL file produces importable stubs that pass mapper lint

---

## v0.9 — Release candidate

**Theme:** Freeze the public API, ship docs and reference apps, burn down rough edges.

### Planned

#### API freeze

- **RFC process** — documented workflow for API changes during RC
- **Contract test suite** — public API surface locked; CI gate on signature and behavior changes
- **Deprecation policy** — `DeprecationWarning` cycle before removals
- **RC releases** — `0.9.0rc1`, `rc2`, … with no new features, only fixes

#### Documentation and examples

- **Documentation site** — MkDocs (or equivalent); tutorials, how-to guides, API reference
- **Production examples** — auth, pagination, multi-map apps, hybrid SQL + graph
- **Compatibility matrix** — Python, SQLModel, Pydantic, FastAPI, TripleModel, SparqlModel
- **Upgrade guides** — `0.2.x → 0.9` migration notes per minor version

#### Hardening

- **Security pass** — review SQL compilation for injection surfaces; document parameter binding guarantees
- **Performance benchmarks** — published numbers for read, write, export at 1k / 10k rows
- **Fuzz / property tests** — query expression compilation invariants

### Success criteria

- Two consecutive RC releases with no API changes and no P0/P1 bugs
- Docs site covers quickstart → CRUD → export → hybrid graph sync
- External contributor can implement a new map using docs alone

---

## v1.0 — Stable platform (GA)

**Theme:** Commit to semver and long-term maintenance.

### Planned

- **API stability guarantee** — `ontosql`, `ontosql.fastapi`, `ontosql.export` follow semver; breaking changes only in 2.0+
- **Support policy** — which Python / dependency versions receive patches
- **1.0 migration guide** — final checklist from `0.9.x`
- **PyPI classifiers** — Development Status :: 5 - Production/Stable
- **Announced GA** — blog/changelog; coordinate with TripleModel / SparqlModel stable releases where practical

### Success criteria

- Documented upgrade path from 0.2.x → 1.0 with no undocumented breaking changes
- All public APIs typed and covered by contract tests
- At least one production deployment reference (internal or documented case study)

---

## Long-term (post-1.0)

Strategic directions, not committed milestones:

| Direction | Description |
|-----------|-------------|
| **AI extraction** | Structured LLM output into `OntoModel` types (`ontosql[ai]`) |
| **OWL tooling** | Optional reasoning via Owlready2 |
| **Polars / ETL** | Ontology-aware DataFrame pipelines over semantic rows |
| **Entity resolution** | Link instances across datasets via shared IRIs |
| **LLM semantic memory** | Typed knowledge snippets for RAG backends |
| **Codegen** | OWL/RDFS → `OntoModel` + `OntoMapper` stubs (build on TripleModel codegen) |

---

## Explicit non-goals

OntoSQL will not replace:

- Full OWL reasoners or ontology IDEs (e.g. Protégé)
- Native graph query languages as the primary application API
- General-purpose ETL or data-lake orchestration
- Automatic 1:1 ORM inference from tables to ontology classes

Focus stays on **explicit maps** and **Pythonic semantic models**, with RDF as interoperability output.

---

## How milestones are chosen

1. **Mapper-first** — no feature that bypasses `OntoMapper` metadata
2. **Pydantic ergonomics** — app code uses semantic types, not row dumps
3. **Standards alignment** — JSON-LD 1.1, RDF 1.1 serializations, SHACL where applicable
4. **Optional weight** — heavy deps in extras (`fastapi`, `sparql`, `shacl`, `jsonld`)
5. **Incremental delivery** — each minor version ships documented, testable scope
6. **Ecosystem reuse** — TripleModel for RDF; SparqlModel for graph ORM — avoid parallel serialization stacks

Feedback welcome via [GitHub Issues](https://github.com/eddiethedean/ontosql/issues).

## Related packages

| Package | Role in ecosystem |
|---------|-------------------|
| [triplemodel](https://github.com/eddiethedean/triplemodel) | Core RDF dependency — export, CURIEs, future import/SHACL |
| [sparqlmodel](https://github.com/eddiethedean/sparqlmodel) | Optional (`ontosql[sparql]`) — graph sessions, SPARQL, hybrid sync |

### Upstream TripleModel tracking issues

Cross-ecosystem work is tracked in [triplemodel #12–#25](https://github.com/eddiethedean/triplemodel/issues). OntoSQL adopts these APIs rather than reimplementing RDF plumbing.
