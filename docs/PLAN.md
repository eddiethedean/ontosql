# OntoSQL Project Plan

## Vision

Build **ontosql** — a Python package that lets teams use **semantic, ontology-shaped models** for application logic while persisting to **existing SQL schemas** through explicit maps. Developers keep SQLModel for tables, Pydantic for concepts, and gain JSON-LD, RDF, and FastAPI interoperability from the same definitions.

```bash
pip install ontosql
```

## Core thesis

**Pythonic semantic CRUD over SQL via explicit maps.**

Real platforms have legacy schemas, bridge tables, and multiple views of the same data. OntoSQL compiles semantic operations to SQL instead of coupling ontology shape to table layout.

## Primary goals

- **Mapper-first** — reviewable bindings between semantic fields and SQL (columns, joins, nested maps)
- **Pydantic ergonomics** — semantic models are what application code imports
- **SQLModel for physical schema** — tables and FKs stay explicit and migration-friendly
- **Session runtime** — `get`, `find`, `save`, `delete` without hand-written JOIN strings for common cases
- **Interop as derivative** — JSON-LD, RDF, SHACL, and FastAPI negotiation from map metadata
- **Ecosystem alignment** — TripleModel for RDF serialization; SparqlModel for optional graph-side tooling
- **Standards without RDF ceremony** — TripleModel stays internal where possible

## Target users

- Enterprise data platform teams bridging operational SQL and knowledge graphs
- Knowledge graph engineers exposing relational data semantically
- AI/RAG platform developers needing typed, IRI-identified entities
- FastAPI backend teams with metadata or interoperability requirements
- Government and defense metadata systems
- Research and biomedical platforms with ontology constraints

## MVP scope (0.2.0)

Version 0.2.0 delivers:

- `OntoModel` and `onto_property` (semantic layer)
- `OntoMapper`, `Map`, `Map.nested` (mapping layer)
- `OntoSession` and `AsyncOntoSession` read path: `get`, `find`, semantic filters
- `PrefixRegistry` (IRI and JSON-LD context; CURIE expand via TripleModel)
- `to_jsonld()` / `to_rdf()` export on semantic instances (TripleModel)
- Architecture, ecosystem, and specification documentation

Write path (`save`, `delete`, cascades) follows in 0.2.x / 0.3 — see [ROADMAP.md](ROADMAP.md).

## Non-goals

- Full OWL reasoning engine
- Native graph database as the primary store
- Complex ontology editing UI
- Replacing Protégé or RDF-native tooling
- Magical inference from SQLAlchemy models to ontology classes without maps
- Owning Alembic or schema migration workflows

## Suggested stack

| Layer | Packages |
|-------|----------|
| Semantic models | Pydantic v2 |
| Physical models | SQLModel, SQLAlchemy 2.x |
| Runtime | OntoSQL session + compile |
| RDF / export | TripleModel (core), pyoxigraph |
| Graph ORM (optional) | SparqlModel (`ontosql[sparql]`) |
| API | FastAPI (optional extra) |
| Validation (future) | pySHACL |
| HTTP (tests) | httpx |
| Typing | typing_extensions |

## Roadmap summary

| Version | Focus |
|---------|--------|
| **0.2.0** | Mapper + session read |
| **0.2.x** | Export polish (TripleModel ecosystem APIs) |
| **0.3** | Write path (`save` / `delete`), `OntoRouter`, OpenAPI |
| **0.4** | RDF import, graph sync (`ontosql[sparql]`), SHACL |
| **0.5** | Advanced maps, batch export, scale |
| **0.6** | Query power, `explain`, mapper lint |
| **0.7** | Bulk write, observability, production FastAPI patterns |
| **0.8** | Schema packs, OWL codegen |
| **0.9** | API freeze, docs site, RC releases |
| **1.0** | GA, semver guarantee, support policy |

Details: [ROADMAP.md](ROADMAP.md). API contract: [SPECS.md](SPECS.md).

## Long-term vision

OntoSQL becomes the default **operational semantic layer** for Python + SQL:

- Typed knowledge graphs backed by Postgres (or any SQLAlchemy dialect)
- AI semantic memory with stable IRIs
- Metadata governance and standards-compliant export
- Enterprise interoperability without abandoning relational operations

## Related documents

- [ECOSYSTEM.md](ECOSYSTEM.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SPECS.md](SPECS.md)
- [DEPS.md](DEPS.md)
