# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Graph sync** — updates apply after SQL commit on session exit, not immediately on `save()`; rolled-back sessions discard queued graph updates
- **Graph sync on delete** — `delete()` queues subgraph removal via `remove_instance`
- **`push_instance` / `GraphSyncTarget`** — patch mode mutates `target.graph` in place (fixes SparqlModel adapter)
- **REPLACE cascade** — nulls parent FK before deleting old nested row; raises `ExecuteError` when a shared nested row is still referenced
- **Session snapshots** — keyed by `(entity_type, identity)` instead of `id(instance)` for stable REPLACE behavior
- **Import coercion** — hardened type coercion for JSON-LD / RDF import paths
- **FastAPI `OntoRouter`** — POST/PATCH validate request bodies with generated Pydantic models before construct/patch

### Changed

- Documentation pass: standalone examples, quick start bootstrap, graph sync timing, cascade policies guide, FAQ, troubleshooting, security notes

## [0.4.0] - 2026-06-25

### Added

- **RDF import** — `ontosql.import_` with `import_from_jsonld`, `import_from_rdf`, `graph_to_instance`; `OntoModel.from_jsonld()`
- **Graph sync** — `ontosql.sync` with `push_instance`, `StoreSyncTarget`, `sync_instance_to_store` (`add` / `replace` / `patch` modes)
- **Session graph hook** — `OntoSession` / `AsyncOntoSession` `graph_sync` and `graph_sync_mode` queue graph updates on `save()` / `delete()` and apply after commit
- **SparqlModel adapter** — `OntoGraphSync` push/pull (`ontosql.sync.sparql`)
- **Materialized views** — `materialize_find`, `materialize_entity`
- **SHACL** — `ontosql.shacl` shape generation and `validate_instance`; optional `ontosql[shacl]` extra (pyshacl)
- **Prefix bundles** — `PrefixRegistry.curated("schema_org" | "dcterms")`
- [HYBRID.md](https://github.com/eddiethedean/ontosql/blob/main/docs/HYBRID.md) and [examples/hybrid_person_org.py](https://github.com/eddiethedean/ontosql/blob/main/examples/hybrid_person_org.py)

### Changed

- **`CascadePolicy.REPLACE`** — deletes old nested row when FK changes or nested becomes `None` (snapshot-based)
- Export honors `onto_property(datatype=..., language=...)` on literals
- CI coverage threshold lowered to 90%

## [0.3.1] - 2026-06-10

### Added

- PyPI release workflow (`.github/workflows/release.yml`) on `v*.*.*` tags

### Changed

- Test suite refactored for behavioral integration coverage; CI coverage threshold 94%
- `OntoRouter` list `limit` capped at 100 via FastAPI `Query(le=100)`
- Documentation: `OntoRouter` production limitations; `CascadePolicy.REPLACE` reserved (same as upsert until 0.4); export uses semantic `onto_property` metadata only; `docs/DEPS.md` synced with `pyproject.toml`

### Fixed

- `ExecuteError` raised when executing delete plans without a `where` clause
- PyLD optional dependency pinned to `>=3.0` (PyPI max is 3.0.0)
- UPSERT nested insert with `id=None` now propagates inserted FK into parent row

## [0.3.0] - 2026-06-10

### Added

- **Write path** — `OntoSession.save()` / `delete()`, `flush()`, `rollback_pending()`, identity map, partial updates
- **`CascadePolicy`** — `link`, `upsert`, `replace`, `ignore` on `Map.nested(..., cascade=, fk_column=)`
- **Query** — nested `FieldPath` (`Person.employer.name`), `contains` / `endswith`, `OrderBy(desc=)`, `paginate()` / `Page`
- **`OntoRouter`** — FastAPI CRUD routes with content negotiation; `onto_session_lifespan`, OpenAPI enrichment
- Optional **`ontosql[jsonld]`** extra — `compact_jsonld` / `frame_jsonld` (PyLD)
- **TripleModel** (`triplemodel>=0.12.0`) as core RDF dependency
- `OntoModel.to_jsonld()` and `to_rdf()`; `ontosql.export` helpers
- Optional `ontosql[sparql]` extra; [ECOSYSTEM.md](https://github.com/eddiethedean/ontosql/blob/main/docs/ECOSYSTEM.md)

### Changed

- `PrefixRegistry.expand()` delegates to TripleModel `expand_curie()`
- Examples: full CRUD demo and `examples/person_org_api.py`

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
- Documentation: [ARCHITECTURE.md](https://github.com/eddiethedean/ontosql/blob/main/docs/ARCHITECTURE.md), [SPECS.md](https://github.com/eddiethedean/ontosql/blob/main/docs/SPECS.md), [ROADMAP.md](https://github.com/eddiethedean/ontosql/blob/main/docs/ROADMAP.md)

[0.3.1]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.1
[0.3.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.0
[0.2.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.2.0
