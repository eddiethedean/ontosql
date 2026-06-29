# Glossary

Terms used across OntoSQL documentation. See also [ARCHITECTURE.md](ARCHITECTURE.md).

| Term | Meaning |
|------|---------|
| **Semantic model / entity** | Pydantic `OntoModel` — what application code and APIs use |
| **Physical model / row model** | SQLModel with `table=True` — mirrors database tables |
| **Map / mapper** | `OntoMapper` — declarative binding from semantic fields to SQL columns and joins |
| **Session** | `OntoSession` or `AsyncOntoSession` — unit of work; compiles CRUD to SQL |
| **Identity** | Primary key value for `get(Person, identity=…)` — mapper-defined id field |
| **Cascade policy** | `link`, `upsert`, `replace`, or `ignore` — controls nested writes on `save()` |
| **Field path** | Nested query reference, e.g. `Person.employer.name` |
| **CURIE** | Compact IRI like `schema:Person` — expanded via `PrefixRegistry` |
| **JSON-LD** | JSON serialization of RDF with `@context` |
| **Graph sync** | Post-commit push of semantic instances to an RDF graph target |
| **Split-brain** | SQL committed but graph sync failed or lagging — see [graph sync ops](guides/graph-sync-operations.md) |
| **OntoRouter** | FastAPI CRUD scaffold — requires host-app auth |
| **TripleModel** | Core RDF library dependency — export and CURIE expansion |
| **SparqlModel** | Optional graph-native ORM sibling — `ontosql[sparql]` |
| **OBDA** | Ontology-Based Data Access — OntoSQL is **not** a SPARQL-to-SQL OBDA engine |
| **Beta-stable API** | Root exports and core packages — additive changes until 1.0 — [SPECS](SPECS.md) |

## Related

- [When to use OntoSQL](getting-started/when-to-use.md)
- [Ecosystem](ECOSYSTEM.md)
