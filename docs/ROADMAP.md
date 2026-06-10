# OntoSQL Roadmap

This document describes planned releases for **ontosql**. For the API contract, see [SPECS.md](SPECS.md). For dependency choices, see [DEPS.md](DEPS.md). For architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Vision

OntoSQL is the **operational semantic layer** for Python apps on SQL: define relational schemas with SQLModel, define application concepts with Pydantic semantic models, connect them with explicit maps, and get CRUD plus JSON-LD/RDF/FastAPI from one source of truth.

OntoSQL shares RDF infrastructure with [TripleModel](https://github.com/eddiethedean/triplemodel) and aligns with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) for graph-native workloads — see [ECOSYSTEM.md](ECOSYSTEM.md).

## Shipped (0.2.0 + unreleased on `main`)

| Area | Status |
|------|--------|
| `OntoModel`, `onto_property` | Shipped |
| `OntoMapper`, `Map`, `Map.nested` | Shipped |
| `OntoSession` / `AsyncOntoSession` `get` / `find` | Shipped |
| Semantic query expressions | Shipped |
| `PrefixRegistry` | Shipped (CURIE expand via TripleModel) |
| Export (`to_jsonld`, `to_rdf`) | Shipped (TripleModel serializers) |
| `ontosql.export` module | Shipped |
| TripleModel core dependency | Shipped |
| `ontosql[fastapi]` content negotiation | Shipped |
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

## v0.3 — Write path and API layer

**Theme:** Full CRUD over SQL and production FastAPI wiring.

### Planned

#### Session write path

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

## v0.4 — Validation and graph interoperability

**Theme:** Close the loop between SQL operational stores and RDF graphs.

### Planned

#### RDF import and sync

- **RDF import** — hydrate `OntoModel` instances from JSON-LD / Turtle (via TripleModel reverse import ([#20](https://github.com/eddiethedean/triplemodel/issues/20)))
- **Graph sync adapters** — push/pull between `OntoSession` and `SPARQLSession` (`ontosql[sparql]`)
- **Incremental sync** — subject-scoped graph diff on `save` ([#23](https://github.com/eddiethedean/triplemodel/issues/23))
- **SPARQL endpoint helpers** — read-only materialized views of exported graphs

#### Validation and shapes

- **SHACL generation** — `NodeShape`s from maps and semantic field types ([#21](https://github.com/eddiethedean/triplemodel/issues/21))
- **`ontosql[shacl]` extra** — optional pySHACL validation of exported graphs

#### Ecosystem alignment

- **Shared prefix bundles** — adopt TripleModel curated vocab defaults ([#24](https://github.com/eddiethedean/triplemodel/issues/24))
- **Hybrid deployment guide** — SQL system of record + SparqlModel metadata graph

### Success criteria

- Export → import preserves `@id`, `@type`, and mapped properties for Person / Organization
- `OntoSession.save()` can push a semantic instance to an in-memory `SPARQLSession` with matching IRIs
- SHACL shapes validate graphs produced by session + export

---

## v0.5 — Mapper ergonomics and scale (tentative)

**Theme:** Advanced mapping patterns and operational hardening before 1.0.

### Planned

- **`Map.computed`** — read-only semantic fields from SQL expressions
- **Multi-map views** — one table → multiple semantic entities (`schema:Person` vs `foaf:Person`)
- **Bridge / join tables** — first-class many-to-many mapper patterns
- **Batch export** — `models_to_graph` for `find` result sets
- **Dialect notes** — Postgres JSON, UUID, array columns in maps
- **Performance** — compiled plan caching; N+1 avoidance on nested `find`

### Success criteria

- Documented patterns for bridge tables and polymorphic semantic views
- Batch export of 1k+ instances without per-row graph allocation hotspots

---

## v1.0 — Stable platform

**Theme:** Production-ready public API and documentation site.

### Planned

- **API stability** — semver policy for `ontosql`, `ontosql.fastapi`, and `ontosql.export`
- **Schema packs** — curated prefix bundles (schema.org, Dublin Core, SKOS) aligned with TripleModel
- **Production examples** — auth, pagination, multi-map apps, hybrid SQL + graph
- **Documentation site** — MkDocs or equivalent; tutorials and API reference
- **Compatibility matrix** — Python, SQLModel, Pydantic, FastAPI, TripleModel, SparqlModel

### Success criteria

- Documented upgrade path from 0.2.x → 1.0
- No breaking changes without a major version and migration guide
- All public APIs typed and covered by contract tests

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
