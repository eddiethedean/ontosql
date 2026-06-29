# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Session `registry=`** — optional `PrefixRegistry` on `OntoSession` / `AsyncOntoSession` for post-commit graph sync
- **`AsyncOntoSession.__del__`** — `ResourceWarning` when session opened but not closed (parity with sync)
- **PyLD safety** — `safe_document_loader` blocks remote `@context` fetches by default; `allow_remote_contexts` opt-in
- Documentation audit: slim README, beta banners, [when-to-use](getting-started/when-to-use.md), [semantic queries](guides/semantic-queries.md), [FastAPI quick start](guides/fastapi-quickstart.md), mkdocstrings [API reference](reference/session.md), expanded FAQ/troubleshooting, SPECS drift fixes
- **Enterprise adoption** — [enterprise-adoption.md](enterprise-adoption.md) evaluation + checklist, [SUPPORT.md](SUPPORT.md), [compliance guide](guides/compliance.md)
- **Operations guides** — [Alembic](guides/alembic.md), [testing](guides/testing.md), [upgrading](guides/upgrading.md), [graph sync runbook](guides/graph-sync-operations.md)
- **API reference** — [FastAPI](reference/fastapi.md), [export](reference/export.md), [import](reference/import.md), [sync](reference/sync.md), [SHACL](reference/shacl.md); [GLOSSARY.md](GLOSSARY.md)

### Fixed

- **UPSERT cascade** — clearing a nested association (`employer=None`) now nulls the FK on update
- **REPLACE exclusivity** — inbound FK checks span all registered mappers (cross-table references block delete)
- **Session snapshots** — DB nested FK values merged into session snapshot for REPLACE compile
- **Graph sync** — stale nested RDF subjects retracted on patch/replace; exclusive nested removed on root delete
- **`OntoSession.flush()`** — partial failure preserves unprocessed queue; deferred insert merges PK into caller instance
- **Identity map** — pending deletes hidden from `get()`; `get(iri=)` respects cached instance; duplicate deferred saves deduplicated
- **`execute_write_plan`** — raises on zero-row UPDATE; raises when collection writes lack parent identity
- **`OntoRouter`** — `limit` ge=1; unified Accept negotiation for list JSON-LD; malformed/deep JSON → 400; `application/json` plain JSON
- **`load_graph`** — invalid UTF-8 raises `OntoImportError`

### Changed

- **`rollback()`** — default `clear_uow=True` (was `False`); warns when `clear_uow=False` leaves pending work
- **`execute_write_plan` / `async_execute_write_plan`** — accept optional `mapper_registry=` and `strict_updates=` (default strict)

## [0.5.1] - 2026-06-29

Documentation and hardening release following 0.5.0.

### Added

- **Read the Docs** — `.readthedocs.yaml` for MkDocs builds; `site_url` uses `READTHEDOCS_CANONICAL_URL` with GitHub Pages fallback
- **Docs site refresh** — landing hero, path cards, tabbed nav, custom theme/CSS, [Start here](guides/start-here.md)
- **Observability** — `ontosql` logger with debug/warning hooks at session commit, flush, and graph sync boundaries
- **RDF import guards** — `max_bytes` and `max_triples` on `load_graph` / `import_from_rdf`
- **OntoRouter** — `validate_entities` and `max_body_bytes` options; `onto_async_session_lifespan` for `AsyncSessionDep`
- **Docs** — [production-router.md](guides/production-router.md), graph split-brain reconciliation in [HYBRID.md](HYBRID.md), [session-lifecycle.md](internals/session-lifecycle.md)
- **Exports** — `GraphSyncError`, `GraphSyncFailure`, `GraphSyncMode`, `OntoImportError`, `paginate_async` from root; `materialize_find_async`, `GraphSyncTarget` from `ontosql.sync`
- **Session API** — `get(identity=)`, `save(flush_now=)`, `clear_pending()`; import helpers take `mapper` positionally; `get_global_registry()` removed
- Shared session orchestration helpers in `ontosql.session._ops`; public API stability tiers in [SPECS.md](SPECS.md)
- Postgres integration tests expanded in CI; onboarding templates and progressive quick start tiers

### Security

- **`OntoRouter`** — async `AsyncSessionDep` on all routes; default `validate_entities=True` and `max_body_bytes=65536`; `dependencies=` for authn/authz; safer `Content-Length` handling (400 on invalid header)
- **RDF import** — `untrusted=True` applies default byte/triple caps; `max_nesting_depth` on `graph_to_instance` (default 32); documented post-parse `max_triples` limit and PyLD SSRF risk
- **Semantic filters** — reject raw `sqlalchemy.text()` in `compile_expr`
- **`GraphSyncFailure`** — exported from `ontosql.session` only (not root `import ontosql`)

### Changed

- **Maintainability** — docs reconciled for 0.5.x; `OntoRouter` list JSON-LD uses `instances_to_jsonld`; mapper identity field validated at registration; `rollback(clear_uow=)`; unified write executors; `column`/`nested`/`computed`/`collection` map functions; expanded API contract tests; sync/async session parity tests
- **Simplicity audit** — removed `materialize_entity`, `patch_subject`, `replace_subject`, `execute_sql`, `OntoModel.registry`, `onto_property(graph=)`, session `registry=` kwarg; `push_instance`/`sync_instance_to_store` require explicit `mapper`; shared RDF helpers in `semantic/rdf_util.py`; consolidated FastAPI list RDF negotiation
- **SHACL** — `shapes_from_mapper` now sets `sh:minCount` to `1` for required scalar properties
- **Async session** — `save()` snapshot resolution aligned with sync session via shared `session/_ops.py`

### Fixed

- **Graph sync** — partial failures after SQL commit preserve the remaining queue; raises `GraphSyncError` with `retry_graph_sync()` for recovery
- **Session flush** — mid-flush errors no longer drop unprocessed pending plans
- **Sync session** — SQLAlchemy session opens in `__enter__`; use as context manager (warns on leak via `ResourceWarning`)

## Migrating from 0.4.x to 0.5.x

0.5.0 is **additive** for most applications. No changes are required unless you adopt new features.

### New capabilities (optional)

- **`Map.computed`** — read-only SQL expression fields; excluded from `save()`; filterable and orderable
- **`Map.collection`** — many-to-many bridge tables with explicit cascade policies; see [bridge-tables.md](guides/bridge-tables.md)
- **Batch export** — `instances_to_graph`, `instances_to_jsonld`, `instances_to_rdf` for efficient multi-instance RDF
- **Select-plan cache** — internal performance improvement; no API change

### Behavior notes

- **`materialize_find`** now builds one `Store` via batch export (same RDF intent, different memory profile)
- **`CascadePolicy.REPLACE`** (from 0.4.0) deletes old nested rows when associations change — do not use on shared nested entities; see [cascade-policies.md](guides/cascade-policies.md)
- **`OntoRouter`** requires auth `dependencies` and async lifespan for public exposure; see [SECURITY.md](SECURITY.md)
- **Graph sync** is eventual-consistency after SQL commit, not two-phase commit; see [HYBRID.md](HYBRID.md)

### API stability (0.5.x)

Until **1.0**, minor releases may add APIs and fix bugs. Breaking changes are reserved for **2.0+** per [ROADMAP.md](ROADMAP.md). Semver guarantees begin at 1.0.

## [0.5.0] - 2026-06-29

### Added

- **`Map.computed`** — read-only semantic fields from SQL expressions; filterable and orderable
- **`Map.collection`** — many-to-many bridge-table mappings with `link` / `upsert` / `replace` / `ignore` cascade policies
- **Batch export** — `instances_to_graph`, `instances_to_jsonld`, `instances_to_rdf`, `write_instance_to_graph`
- **Select-plan cache** — `compile/cache.py` skeleton cache per mapper
- **Batched collection hydration** — one query per collection field after `find` / `get`
- **Guides** — [bridge-tables.md](guides/bridge-tables.md), [multi-map-views.md](guides/multi-map-views.md), [postgres-dialect.md](guides/postgres-dialect.md)
- **Example** — `examples/multi_map_person.py`
- RDF import hydrates `Map.collection` list fields

### Changed

- `materialize_find` uses `instances_to_graph` (single `Store` allocation)
- `ComputedMap` / `CollectionMap` exported from `ontosql.mapping`

## [0.4.0] - 2026-06-25

### Added

- **RDF import** — `ontosql.import_` with `import_from_jsonld`, `import_from_rdf`, `graph_to_instance`; `OntoModel.from_jsonld()`
- **Graph sync** — `ontosql.sync` with `push_instance`, `remove_instance`, `StoreSyncTarget`, `sync_instance_to_store` (`add` / `replace` / `patch` modes)
- **Session graph hook** — `OntoSession` / `AsyncOntoSession` `graph_sync` and `graph_sync_mode` queue graph updates on `save()` / `delete()` and apply after commit
- **SparqlModel adapter** — `OntoGraphSync` push/pull (`ontosql.sync.sparql`)
- **Materialized views** — `materialize_find`, `materialize_entity`
- **SHACL** — `ontosql.shacl` shape generation and `validate_instance`; optional `ontosql[shacl]` extra (pyshacl)
- **Prefix bundles** — `PrefixRegistry.curated("schema_org" | "dcterms")`
- **Documentation site** — MkDocs + Material theme; `pip install ontosql[docs]`; CI `mkdocs build --strict`
- **Contributor docs** — `CONTRIBUTING.md`, FAQ, troubleshooting, security notes, cascade policies guide, compatibility matrix
- Standalone PyPI-runnable examples (`examples/models.py`); async session example
- [HYBRID.md](https://github.com/eddiethedean/ontosql/blob/main/docs/HYBRID.md) and [examples/hybrid_person_org.py](https://github.com/eddiethedean/ontosql/blob/main/examples/hybrid_person_org.py)

### Changed

- **`CascadePolicy.REPLACE`** — deletes old nested row when FK changes or nested becomes `None` (snapshot-based)
- Export honors `onto_property(datatype=..., language=...)` on literals
- CI coverage threshold lowered to 90%
- Documentation pass: quick start bootstrap, graph sync timing, shipped vs planned labels in ecosystem docs

### Fixed

- **Graph sync** — updates apply after SQL commit on session exit, not immediately on `save()`; rolled-back sessions discard queued graph updates
- **Graph sync on delete** — `delete()` queues subgraph removal via `remove_instance` only after SQL delete succeeds
- **`push_instance` / `GraphSyncTarget`** — patch mode mutates `target.graph` in place (fixes SparqlModel adapter)
- **Graph patch root IRI** — uses `build_instance_iri(instance)` instead of nondeterministic set iteration
- **Shared nested graph nodes** — nested subjects patched by owned predicates only; delete removes root subject only
- **REPLACE cascade** — nulls parent FK before deleting old nested row; raises `ExecuteError` when a shared nested row is still referenced
- **Session snapshots** — keyed by `(entity_type, identity)` instead of `id(instance)` for stable REPLACE behavior
- **Detached updates** — load DB snapshot when session snapshot missing so REPLACE and updates work without prior `get()`
- **Pending writes** — `save(flush_now=False)` / `delete(flush_now=False)` auto-flush on session exit; `clear_pending()` clears graph sync queues
- **Import** — `model_validate` after hydrate; `Optional[T]` / `int | None` coercion
- **FastAPI `OntoRouter`** — POST/PATCH validate bodies with generated Pydantic models; PATCH cannot retarget row via body `id`; list supports RDF `Accept` headers; `offset` validated `ge=0`
- Invalid `graph_sync_mode` raises `ValueError` instead of silent no-op

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

- **Write path** — `OntoSession.save()` / `delete()`, `flush()`, `clear_pending()`, identity map, partial updates
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

[0.5.1]: https://github.com/eddiethedean/ontosql/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.5.0
[0.4.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.4.0
[0.3.1]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.1
[0.3.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.0
[0.2.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.2.0
