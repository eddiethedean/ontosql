# SemSQL Roadmap

This document describes planned releases and long-term direction for **semsql**. For implementation details, see [SPECS.md](SPECS.md). For dependency choices, see [DEPS.md](DEPS.md).

## Vision

SemSQL is the operational semantic layer for Python apps built on SQLModel and FastAPI. Developers define relational models once, attach ontology metadata in place, and gain JSON-LD and RDF interoperability without adopting a separate RDF-native stack.

## Current release: 0.1.0

**Status: shipped**

| Area | Delivered |
|------|-----------|
| Core API | `OntoMixin`, `onto_field()`, `@onto_model`, `apply_onto_model()` |
| Serialization | `to_jsonld()`, `to_rdf()` (Turtle, JSON-LD, N-Triples, RDF/XML) |
| Context | `PrefixRegistry`, class-level `onto_context()` |
| Literals | JSON-safe coercion for `datetime`, `date`, `UUID`, `Decimal`, `Enum`, `tuple` |
| Relationships | Nested object export; FK `@id` references; duplicate-property resolution |
| FastAPI | `semsql[fastapi]` — response classes, `negotiate_onto_response()`, RFC-aware `Accept` parsing |
| Quality | 100% test coverage on measured source modules |

### Known limitations (0.1.0)

- Export only — no RDF → SQLModel import
- No SHACL shape generation or validation
- No auto-generated CRUD router (`OntoRouter`)
- No JSON-LD framing (planned via optional PyLD extra)
- FK fields and nested relationship fields should not share the same ontology property

---

## v0.2 — Import and validation

**Theme:** Close the loop between operational data and semantic graphs.

### Planned

- **SHACL generation** — derive `NodeShape`s from SQLModel field types, optionality, and ontology metadata
- **RDF import** — hydrate SQLModel instances from JSON-LD or RDF (Turtle / JSON-LD input)
- **Prefix management** — vocabulary packs, frozen registries, and safer CURIE defaults for common ontologies (schema.org, SKOS, etc.)
- **`semsql[shacl]` extra** — optional `pySHACL` integration for graph validation

### Success criteria

- Round-trip: export → import preserves `@id`, `@type`, and annotated properties
- SHACL shapes validate exported graphs for representative models

---

## v0.3 — API ergonomics

**Theme:** First-class FastAPI and OpenAPI integration.

### Planned

- **`OntoRouter`** — auto-register CRUD routes for annotated models
- **OpenAPI enrichment** — expose ontology IRIs, RDF types, and semantic media types in schema docs
- **`semsql[jsonld]` extra** — PyLD-based compaction and framing
- **Bulk export** — serialize query results (lists of models) to JSON-LD graphs or RDF datasets

### Success criteria

- A minimal demo app can serve CRUD + content negotiation with under 20 lines of wiring code

---

## v0.4 — Graph interoperability

**Theme:** Connect operational stores to graph infrastructure.

### Planned

- **Graph sync adapters** — push/pull between SQLModel-backed tables and graph stores
- **SPARQL endpoint helpers** — publish read-only views of exported graphs
- **Named graph support** — per-field or per-model `graph` metadata in export

### Candidate integrations (extras)

- Neo4j driver (`semsql[graphdb]`)
- SPARQLWrapper for remote endpoints

---

## v1.0 — Stable platform

**Theme:** Production-ready public API and documentation.

### Planned

- **API stability guarantee** — semver policy for public symbols in `semsql` and `semsql.fastapi`
- **Schema packs** — curated prefix bundles (schema.org, Dublin Core, SKOS, etc.)
- **Production examples** — multi-model apps, auth, pagination, and negotiation patterns
- **Full documentation site** — tutorials, API reference, migration guides

### Success criteria

- Documented upgrade path from 0.x → 1.0
- Published compatibility matrix (Python, SQLModel, Pydantic, FastAPI)

---

## Long-term (post-1.0)

These are strategic directions, not committed milestones:

| Direction | Description |
|-----------|-------------|
| **AI extraction** | Structured LLM output into `onto_field` models (`semsql[ai]` — Instructor, PydanticAI) |
| **OWL tooling** | Optional reasoning and ontology editing via Owlready2 |
| **Polars / ETL** | Ontology-aware DataFrame pipelines |
| **Entity resolution** | Link instances across datasets via shared IRIs |
| **LLM semantic memory** | Typed knowledge snippets for RAG backends |

---

## Explicit non-goals

SemSQL will not attempt to replace:

- Full OWL reasoners or ontology IDEs (e.g. Protégé)
- Native graph query languages as the primary application API
- General-purpose ETL or data-lake orchestration

The focus stays on **Pythonic models first**, with RDF as an interoperability layer.

---

## How milestones are chosen

1. **SQLModel ergonomics** — no regression in developer experience
2. **Standards alignment** — JSON-LD 1.1, RDF 1.1 serializations, SHACL where applicable
3. **Optional weight** — heavy dependencies live in extras (`fastapi`, `shacl`, `jsonld`, `graphdb`)
4. **Incremental delivery** — each minor version ships usable, documented features

Feedback and contributions are welcome via [GitHub Issues](https://github.com/eddiethedean/semsql/issues).
