# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-06-29

### Added

- **`ontosql.io`** — `to_jsonld`, `to_rdf`, `from_jsonld` module-level I/O API (preferred over instance methods)
- **`ontosql.ports`** — `SessionBackend`, `PlanExecutor`, `MapperLookup`, `MapperMetadata`, `GraphSyncPort` protocols
- **`ontosql.rdf`** — shared RDF kernel (`literals`, `formats`, `predicates`)
- **`OntoMapper.metadata()`** — neutral field metadata view for RDF/import/sync layers
- **`OntoSession` / `AsyncOntoSession`** — optional `mapper_registry=` for shared `MapperLookup` injection
- **`OntoRouter`** — optional `mapper_registry=` for shared mapper lookup
- **Compile layer split** — `columns`, `nested_write`, `collection_write`, `save_plan`, `execute_runner`
- **Session internals split** — `IdentityMap`, `PendingWorkQueue`, `GraphSyncQueue`, `FlushCoordinator`

### Changed

- **SOLID refactor** — protocol-driven boundaries; unified sync/async flush coordinator and execute runner
- **`OntoModel.to_jsonld` / `to_rdf` / `from_jsonld`** — delegate to `ontosql.io` (instance methods retained as thin wrappers)
- **RDF format helpers** — moved from `ontosql.export._formats` to `ontosql.rdf.formats` (shim retained)

### Migration

See [guides/upgrading.md](docs/guides/upgrading.md#05x--06x).

## [0.5.0] - 2026-06-29

### Added

- **`Map.computed`** — read-only semantic fields from SQL expressions; filterable and orderable
- **`Map.collection`** — many-to-many bridge-table mappings with `link` / `upsert` / `replace` / `ignore` cascade policies
- **Batch export** — `instances_to_graph`, `instances_to_jsonld`, `instances_to_rdf`, `write_instance_to_graph`
- **Select-plan cache** — `compile/cache.py` skeleton cache per mapper
- **Batched collection hydration** — one query per collection field after `find` / `get`
- **`AsyncOntoSession.create_tables()`** and **`session.expire_all()`**
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
- **Session graph sync** — pre-save nested IRIs captured at queue time (stale nested retraction works via session path)
- **Graph sync collections** — `Map.collection` predicates owned in patch mode; collection member IRIs tracked for stale removal
- **`find()`** — excludes pending-delete tombstones (consistent with `get()`)
- **Session lifecycle** — exception exit clears pending queue; flush failure preserves deferred-insert identity mapping
- **Snapshot merge** — DB-null nested FK overrides stale session nested dict
- **Accept negotiation** — `application/json` participates in q-value sorting with RDF types
- **Import** — non-URI collection members raise `OntoImportError`; duplicate collection IRIs deduplicated
- **Write execute** — collection bridge sync runs before REPLACE nested deletes on update
- **Deferred graph sync** — `prior_nested_iris` captured at deferred `save()` queue time
- **Partial flush** — graph sync queue restored on flush failure; `rollback()` always clears graph sync queue
- **`count()`** — subtracts pending-delete tombstones (consistent with `get()` / `find()`)
- **Delete graph sync** — nested IRIs from pre-delete DB/session snapshot when fields unset
- **Delete SQL cascade** — `REPLACE` nested rows deleted on root `delete()` when exclusively owned
- **Collection `REPLACE`** — orphan member rows removed when collection membership shrinks
- **Snapshot merge** — empty DB collection lists no longer overwrite session collection snapshots
- **Import** — multi-valued scalar literals; nested literal objects raise `OntoImportError`
- **Export** — batch export deduplicates by logical IRI
- **`OntoRouter`** — list `GET` defaults to JSON-LD without `Accept`; RDF negotiation returns 406 on unsupported payloads
- **Accept negotiation** — invalid `q` values rejected; `application/*` maps to `application/ld+json`

### Changed

- **`rollback()`** — default `clear_uow=True` (was `False`); warns when `clear_uow=False` leaves pending work
- **`execute_write_plan` / `async_execute_write_plan`** — accept optional `mapper_registry=` and `strict_updates=` (default strict)
- **`execute_write_plan`** — REPLACE nested deletes require `mapper_registry=` (cross-table FK safety)
- **`compile_save_plan`** — REPLACE cascade on update requires `snapshot=`
- **`compact_jsonld` / `frame_jsonld`** — `allow_remote_contexts=True` requires explicit `document_loader=`

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

[0.5.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.5.0
[0.4.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.4.0
[0.3.1]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.1
[0.3.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.3.0
[0.2.0]: https://github.com/eddiethedean/ontosql/releases/tag/v0.2.0
