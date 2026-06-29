# When to use OntoSQL

OntoSQL is the **operational semantic layer** for Python apps on SQL: ontology-shaped Pydantic models, real SQL schemas, explicit maps, optional JSON-LD/RDF from the same definitions.

## Use OntoSQL when

| Scenario | Why OntoSQL |
|----------|-------------|
| **SQL-first app with ontology-shaped APIs** | CRUD over Postgres/SQLite with `schema:Person`-style models and optional RDF export |
| **Legacy SQL schema + semantic API** | Explicit `OntoMapper` bindings — joins, bridges, computed fields — without rewriting tables |
| **Hybrid SQL + RDF** | SQL as system of record; graph mirror on commit ([HYBRID](../HYBRID.md)) |
| **FastAPI with content negotiation** | JSON-LD / Turtle responses from mapper metadata (`ontosql[fastapi]`) |
| **One table, multiple semantic views** | Multiple mappers per physical table ([multi-map views](../guides/multi-map-views.md)) |

## Do not use OntoSQL when

| Scenario | Use instead |
|----------|-------------|
| **Graph is the primary store** | [SparqlModel](https://github.com/eddiethedean/sparqlmodel) |
| **File parse/serialize only** | [TripleModel](https://github.com/eddiethedean/triplemodel) |
| **Standard table CRUD, no ontology layer** | SQLModel / SQLAlchemy directly |
| **Automatic table → ontology inference** | OntoSQL requires **explicit maps** — no magic ORM-to-OWL |
| **Full OWL reasoning or Protégé workflows** | Dedicated reasoners / ontology tools |
| **SPARQL as primary query language** | SparqlModel or a triple store |

## Package comparison

| | SQLModel / SQLAlchemy | OntoSQL | SparqlModel |
|---|----------------------|---------|-------------|
| **Primary store** | SQL tables | SQL tables | RDF graph / SPARQL |
| **Application models** | Row models | `OntoModel` (semantic) | `SPARQLModel` (graph) |
| **Schema mapping** | Typically 1:1 | Explicit `OntoMapper` | Graph-native |
| **RDF / JSON-LD** | Manual | `to_jsonld()` / `to_rdf()` | Native |
| **Migrations** | You own (Alembic) | You own — OntoSQL does not migrate | Store-dependent |

## Do I need RDF?

**No.** Tier 1 of the [quick start](quickstart.md) uses semantic CRUD only. `type_iri` and `iri_template` enable export later; they do not require a graph database.

Enable RDF when you need JSON-LD/Turtle APIs, graph sync, SHACL validation, or interoperability with TripleModel/SparqlModel.

## Read next

- [Quick start](quickstart.md) — pip-only CRUD in minutes
- [Architecture](../ARCHITECTURE.md) — two model layers and explicit maps
- [Ecosystem](../ECOSYSTEM.md) — OntoSQL, TripleModel, SparqlModel boundaries
- [Compatibility](../COMPATIBILITY.md) — Python, databases, beta status
