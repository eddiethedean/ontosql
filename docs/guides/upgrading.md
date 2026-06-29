# Upgrading OntoSQL

Migration notes between versions. Full per-minor guides are planned for **0.9** — [ROADMAP.md](../ROADMAP.md).

!!! tip "Pin versions"
    In production, pin `ontosql==X.Y.Z` until 1.0 semver. Read [COMPATIBILITY.md](../COMPATIBILITY.md) and [SPECS API stability](../SPECS.md#api-stability-05x).

## General upgrade process

1. Read the [changelog](../changelog.md) for your target version
2. Run your integration test suite — [testing guide](testing.md)
3. Search for removed APIs in your codebase (see tables below)
4. Upgrade optional extras together (`async`, `fastapi`, `sparql`, `shacl`)

## 0.5.x → 0.6.x

**Structural SOLID refactor** — behavior preserved; imports and extension points updated.

| Before | After |
|--------|-------|
| `person.to_jsonld()` | `ontosql.to_jsonld(person)` or `from ontosql.io import to_jsonld` |
| `Person.from_jsonld(doc, mapper=...)` | `ontosql.from_jsonld(Person, doc, mapper=...)` |
| `from ontosql.export._formats import ...` | `from ontosql.rdf.formats import ...` |
| Direct `mapper.column_maps` in app code | `mapper.metadata().fields` or `mapper.metadata()` helpers |
| `OntoRouter(maps=...)` only | Optional `mapper_registry=` for shared lookup |
| `OntoSession(engine, maps=...)` only | Optional `mapper_registry=` on `SessionBase` subclasses |

`OntoModel.to_jsonld()` / `to_rdf()` / `from_jsonld()` remain as thin wrappers delegating to `ontosql.io`.

## 0.4.x → 0.5.x

**Mostly additive.** See [changelog migrating section](../changelog.md).

| Topic | Action |
|-------|--------|
| New features | Optional: `Map.computed`, `Map.collection`, batch export |
| `OntoRouter` | Requires async lifespan + auth for public exposure |
| `REPLACE` cascade | Review nested delete behavior — [cascade policies](cascade-policies.md) |
| Graph sync | Eventual consistency after commit — [HYBRID.md](../HYBRID.md) |

No required code changes for basic CRUD if you already pass `maps=[...]` to sessions.

**Removed APIs (0.5.x simplicity audit):**

| Removed | Migration |
|---------|-----------|
| `OntoModel.registry` | Pass `maps=[...]` to `OntoSession` |
| `onto_property(..., graph=)` | Removed; named graphs planned via TripleModel roadmap |
| `execute_sql` on session | Use SQLAlchemy session from your app layer |
| `push_instance` without mapper | Pass `mapper` positionally |
| Root `GraphSyncFailure` import | `from ontosql.session import GraphSyncFailure` |

## 0.3.x → 0.4.x

Major hybrid features added (RDF import, graph sync, SHACL). New optional extras:

```bash
pip install "ontosql[sparql,shacl]"
```

Graph sync timing changed: updates apply **after SQL commit** on session exit, not inside `save()`.

## 0.2.x → 0.3.x

Write path and `OntoRouter` introduced. If upgrading from read-only 0.2.x:

- Add cascade policies to nested `Map.nested` fields
- TripleModel became core RDF dependency
- Replace any custom export with `to_jsonld()` / `ontosql.export` helpers

## Pre-1.0 → 1.0 (future)

Planned:

- Semver guarantee
- Deprecation warnings before removals
- Consolidated `0.2.x → 1.0` migration guide
- Support policy — [SUPPORT.md](../SUPPORT.md)

Track [ROADMAP v0.9 and v1.0](../ROADMAP.md).

## Existing SQLAlchemy applications

OntoSQL is not a drop-in replacement. Migration steps:

1. Define SQLModel row classes for existing tables
2. Author `OntoModel` + `OntoMapper` per entity
3. Gradually route new code through `OntoSession`; keep legacy paths until mappers cover scope
4. Alembic unchanged — [Alembic guide](alembic.md)

## Related

- [changelog](../changelog.md)
- [SPECS.md](../SPECS.md)
- [enterprise adoption](../enterprise-adoption.md)
