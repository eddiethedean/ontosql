# OntoSQL Roadmap

This document describes planned releases for **ontosql**. For the API contract, see [SPECS.md](SPECS.md). For dependency choices, see [DEPS.md](DEPS.md). For architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Vision

OntoSQL is the **operational semantic layer** for Python apps on SQL: define relational schemas with SQLModel, define application concepts with Pydantic semantic models, connect them with explicit maps, and get CRUD plus JSON-LD/RDF/FastAPI from one source of truth.

OntoSQL shares RDF infrastructure with [TripleModel](https://github.com/eddiethedean/triplemodel) and aligns with [SparqlModel](https://github.com/eddiethedean/sparqlmodel) for graph-native workloads — see [ECOSYSTEM.md](ECOSYSTEM.md).

## Current release: 0.2.0

| Area | Status |
|------|--------|
| `OntoModel`, `onto_property` | Shipped |
| `OntoMapper`, `Map`, `Map.nested` | Shipped |
| `OntoSession` / `AsyncOntoSession` `get` / `find` | Shipped |
| Semantic query expressions | Shipped |
| `PrefixRegistry` | Shipped (CURIE expand via TripleModel) |
| Export (`to_jsonld`, `to_rdf`) | Shipped (TripleModel serializers) |
| TripleModel dependency | Shipped |
| `save` / `delete` | Planned 0.2.x / 0.3 |
| `OntoRouter` | Planned 0.3 |
| SparqlModel graph sync (`ontosql[sparql]`) | Planned 0.4 |

---

## v0.2.x / 0.3 — Write path and API ergonomics

**Theme:** Full CRUD, export, and FastAPI integration.

### Planned

- **`save` / `delete`** — insert/update/delete plans across tables; transactions
- **Nested cascade policies** — `link`, `upsert`, `replace`, `ignore` on `Map.nested`
- **Partial updates** — `model_dump(exclude_unset=True)` drives PATCH-style SQL
- **Export enhancements** — literal typing (`datetime`, `LangString`), list-valued properties, mapper-driven export
- **`OntoRouter`** — auto-register CRUD routes
- **OpenAPI enrichment** — ontology IRIs and semantic media types in schema docs
- **Bulk `find`** — lists of semantic instances; pagination helpers
- **`ontosql[jsonld]` extra** — PyLD compaction and framing

### Success criteria

- Round-trip: create → read → update nested association → delete
- Demo app: CRUD + content negotiation in under ~30 lines of wiring

---

## v0.4 — Validation and graph interoperability

**Theme:** Close the loop between SQL and semantic graphs.

### Planned

- **SHACL generation** — `NodeShape`s from maps and semantic field types
- **RDF import** — hydrate semantic instances from JSON-LD / Turtle
- **Graph sync adapters** — push/pull between `OntoSession` and `SPARQLSession` (SparqlModel via `ontosql[sparql]`)
- **SPARQL endpoint helpers** — read-only views of exported graphs
- **`ontosql[shacl]` extra** — optional pySHACL validation

### Success criteria

- Export → import preserves `@id`, `@type`, and mapped properties for representative models
- SHACL shapes validate graphs produced by session + export

---

## v1.0 — Stable platform

**Theme:** Production-ready public API and documentation site.

### Planned

- **API stability** — semver policy for `ontosql` and `ontosql.fastapi`
- **Schema packs** — curated prefix bundles (schema.org, Dublin Core, SKOS)
- **Production examples** — auth, pagination, multi-map apps
- **Documentation site** — MkDocs or equivalent; tutorials and API reference

### Success criteria

- Documented upgrade path from 0.2.x → 1.0
- Compatibility matrix: Python, SQLModel, Pydantic, FastAPI

---

## Long-term (post-1.0)

Strategic directions, not committed milestones:

| Direction | Description |
|-----------|-------------|
| **AI extraction** | Structured LLM output into `OntoModel` types (`ontosql[ai]`) |
| **OWL tooling** | Optional reasoning via Owlready2 |
| **Polars / ETL** | Ontology-aware DataFrame pipelines |
| **Entity resolution** | Link instances across datasets via shared IRIs |
| **LLM semantic memory** | Typed knowledge snippets for RAG backends |

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
4. **Optional weight** — heavy deps in extras (`fastapi`, `shacl`, `jsonld`, `graphdb`)
5. **Incremental delivery** — each minor version ships documented, testable scope
6. **Ecosystem reuse** — TripleModel for RDF; SparqlModel for graph ORM — avoid parallel serialization stacks

Feedback welcome via [GitHub Issues](https://github.com/eddiethedean/ontosql/issues).

## Related packages

| Package | Role in ecosystem |
|---------|-------------------|
| [triplemodel](https://github.com/eddiethedean/triplemodel) | Core RDF dependency — export, CURIEs |
| [sparqlmodel](https://github.com/eddiethedean/sparqlmodel) | Optional — graph sessions, SPARQL, hybrid sync |
