# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **TripleModel** (`triplemodel>=0.12.0`) as core RDF dependency — replaces RDFLib
- `OntoModel.to_jsonld()` and `to_rdf()` — export semantic instances via TripleModel
- `ontosql.export` — `instance_to_graph`, `instance_to_jsonld`, `instance_to_rdf`
- Optional `ontosql[sparql]` extra — SparqlModel for graph-native / hybrid workflows
- [ECOSYSTEM.md](docs/ECOSYSTEM.md) — OntoSQL, TripleModel, and SparqlModel boundaries

### Changed

- `PrefixRegistry.expand()` delegates to TripleModel `expand_curie()`
- Documentation updated across README, ARCHITECTURE, SPECS, PLAN, DEPS, ROADMAP

## [0.2.0] - 2026-05-16

First release of **OntoSQL** — semantic data access for SQL via explicit maps.

### Added

- `OntoModel` and `onto_property` — Pydantic semantic entities with ontology metadata
- `OntoMapper`, `Map`, and `Map.nested` — declarative bindings from semantic fields to SQL columns and joins
- `OntoSession` (sync) and `AsyncOntoSession` — `get`, `find`, and `execute_sql` with semantic query expressions
- `PrefixRegistry` — CURIE expansion, compaction, and JSON-LD `@context`
- Optional `ontosql[fastapi]` extra — content negotiation helpers for dict, string, and future semantic export types
- Integration tests for Person / Organization nested `worksFor` over SQLite (sync and async)
- Example: `examples/person_org_demo.py`
- Documentation: [ARCHITECTURE.md](docs/ARCHITECTURE.md), [SPECS.md](docs/SPECS.md), [ROADMAP.md](docs/ROADMAP.md)

### Planned next

- `save` / `delete` and nested cascade policies (0.2.x / 0.3)
- `to_jsonld` / `to_rdf` on semantic instances (0.2.x)
- FastAPI negotiation wired to session-loaded entities (0.2.x)

[0.2.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.2.0
