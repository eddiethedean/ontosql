# Enterprise adoption evaluation

This page summarizes what a **documentation-only** evaluator can conclude about OntoSQL **0.5.x** for large-organization adoption. It is honest about beta status and known documentation limits.

!!! warning "0.5.x beta"
    OntoSQL is **not GA**. Semver guarantees begin at [1.0](ROADMAP.md). Pin versions and complete the [evaluation checklist](#evaluation-checklist) before production use.

## Overall verdict

OntoSQL is **documented honestly as pre-1.0 beta software** with strong architecture and security transparency. It is suitable for **controlled PoC** (Postgres, pinned version, SQL-first team). Enterprise platform standardization should wait for 1.0, a support policy, and performance evidence.

---

## What does OntoSQL do?

OntoSQL is a **Python semantic data access layer** for SQL-first applications:

| Layer | Tool | Role |
|-------|------|------|
| Physical | SQLModel (`table=True`) | Mirrors real DB tables |
| Semantic | `OntoModel` | Application entities, validation, ontology metadata |
| Mapping | `OntoMapper` / `Map` | Explicit field → column/join bindings |
| Runtime | `OntoSession` / `AsyncOntoSession` | Compiles `get`, `find`, `save`, `delete` to SQL |

Optional extras: JSON-LD/RDF export, RDF import, post-commit graph sync, SHACL, FastAPI `OntoRouter`.

**Not:** SPARQL database, OBDA engine, OWL reasoner, or automatic table→ontology inference. See [When to use OntoSQL](getting-started/when-to-use.md).

---

## Why would I use it?

| Need | OntoSQL value |
|------|----------------|
| Legacy/normalized SQL + ontology-shaped Python APIs | Explicit maps over joins, bridges, computed fields |
| Optional JSON-LD/RDF/FastAPI negotiation | Export from mapper metadata |
| Hybrid SQL system-of-record + RDF mirror | Post-commit `graph_sync` — [HYBRID.md](HYBRID.md) |
| Multiple semantic views of one table | [Multi-map views](guides/multi-map-views.md) |

**Cost:** maintain row models, semantic models, and mappers (three artifacts).

---

## Is it production ready?

**No — and the docs say so.**

| Signal | Source |
|--------|--------|
| PyPI **Development Status :: 4 - Beta** | [COMPATIBILITY.md](COMPATIBILITY.md) |
| Semver from **1.0** only; pre-1.0 may rename without deprecation | [SPECS.md](SPECS.md) |
| `OntoRouter` is a scaffold — auth/authz required | [SECURITY.md](SECURITY.md) |
| Graph sync is **eventually consistent** after SQL commit | [HYBRID.md](HYBRID.md) |
| Bulk write, read replicas, OTel | Planned [0.7](ROADMAP.md) |
| GA / Production/Stable classifier | Planned [1.0](ROADMAP.md) |

**Enterprise interpretation:** PoC with pinned versions — yes. Platform standard — wait for 1.0 + [support policy](SUPPORT.md).

---

## Is it actively maintained?

**Partially documented.**

| Known | Unknown from docs |
|-------|-------------------|
| Release cadence in [changelog](changelog.md) (0.2.0 → 0.5.x) | Maintainer team size, bus factor |
| CI badge, [contributing](contributing.md) workflow | Issue/commit response SLAs |
| Public [roadmap](ROADMAP.md) through 1.0 | Calendar date for 1.0 |
| Read the Docs hosting | Commercial backing or LTS windows (until 1.0) |

See [SUPPORT.md](SUPPORT.md) for current community support model.

---

## How difficult is migration?

| Scenario | Difficulty | Documentation |
|----------|------------|---------------|
| Greenfield app | Moderate | [Quick start](getting-started/quickstart.md) |
| Existing SQLAlchemy/SQLModel app | Moderate–high | Manual maps; [Alembic guide](guides/alembic.md) |
| **0.4.x → 0.5.x** | Low (additive) | [Changelog migration section](changelog.md) |
| **0.2.x → current / pre-1.0 → 1.0** | High | [Upgrading guide](guides/upgrading.md) (partial; full notes at 0.9) |

Migration is **mapper authoring + Alembic coordination**, not a drop-in ORM swap.

---

## How difficult is onboarding?

| Persona | Difficulty | Doc support |
|---------|------------|-------------|
| Python dev, SQLModel familiarity | Low–moderate | Quick start, [semantic queries](guides/semantic-queries.md) |
| Async / FastAPI | Moderate | [async](getting-started/async.md), [FastAPI quick start](guides/fastapi-quickstart.md) |
| Hybrid SQL + RDF | High | [HYBRID.md](HYBRID.md), [graph sync operations](guides/graph-sync-operations.md) |
| Enterprise platform / security | High | This page + [compliance guide](guides/compliance.md) |

**Time-to-first-success (typical):** Tier 1 CRUD 5–15 minutes; production FastAPI hours–days; hybrid graph sync days–weeks.

---

## What are the risks?

### Documented technical risks

| Risk | Severity | Read |
|------|----------|------|
| Pre-1.0 API instability | High | [SPECS](SPECS.md), [COMPATIBILITY](COMPATIBILITY.md) |
| `CascadePolicy.REPLACE` data loss | High | [cascade policies](guides/cascade-policies.md), [SECURITY](SECURITY.md) |
| Graph/SQL split-brain | High | [HYBRID](HYBRID.md), [graph sync ops](guides/graph-sync-operations.md) |
| `OntoRouter` without auth | High | [production-router](guides/production-router.md) |
| RDF import DoS / PyLD SSRF | Medium | [SECURITY](SECURITY.md) |
| TripleModel core dependency (SQL-only apps) | Medium | [COMPATIBILITY](COMPATIBILITY.md) |

### Enterprise / procurement risks

No vendor SLA, performance benchmarks, compliance certifications, or production case studies today. See [compliance guide](guides/compliance.md) and [SUPPORT.md](SUPPORT.md).

---

## Adoption recommendation

| Scenario | Recommendation |
|----------|----------------|
| Enterprise platform standard | **Do not adopt** until 1.0 + support policy + benchmarks |
| Team PoC (Postgres, pinned 0.5.x) | **Proceed with spike** — budget mapper work and security review |
| Hybrid SQL + RDF production | **High caution** — custom reconciliation; see [graph sync ops](guides/graph-sync-operations.md) |
| Public `OntoRouter` | **Reject default scaffold** — custom auth/authz only |

---

## Evaluation checklist

Use this before approving OntoSQL beyond a time-boxed PoC.

### Fit and scope

- [ ] Read [When to use OntoSQL](getting-started/when-to-use.md) — confirm you need semantic layer, not raw SQLModel or SparqlModel
- [ ] Confirm **Postgres or SQLite** (only CI-tested DBs) — [COMPATIBILITY](COMPATIBILITY.md)
- [ ] Accept **0.5.x beta** and pin `ontosql==…` in requirements
- [ ] Budget **mapper authoring** for every entity (no auto-inference)

### Security and API

- [ ] If exposing HTTP: **do not** mount `OntoRouter` without `dependencies=[Depends(auth)]` — [SECURITY](SECURITY.md)
- [ ] Object-level authorization designed for `{entity_id}` and nested POST/PATCH bodies
- [ ] Rate limits at proxy or middleware
- [ ] RDF import endpoints authenticated; `untrusted=True` and byte/triple caps
- [ ] Review [compliance guide](guides/compliance.md) for questionnaire gaps

### Data and operations

- [ ] Alembic owns physical schema; mappers updated with column changes — [Alembic guide](guides/alembic.md)
- [ ] Cascade policy per nested field reviewed (`link` default; avoid `REPLACE` on shared rows)
- [ ] If `graph_sync`: split-brain runbook, monitoring, `retry_graph_sync` — [graph sync ops](guides/graph-sync-operations.md)
- [ ] SQLite production: `PRAGMA foreign_keys=ON` if using REPLACE cascade

### Quality and upgrades

- [ ] Adopter test plan — [testing guide](guides/testing.md)
- [ ] Upgrade path documented for your version jump — [upgrading](guides/upgrading.md)
- [ ] API review: [Session](reference/session.md), [Mapping](reference/mapping.md), [Query](reference/query.md), [I/O](reference/io.md), [SPECS](SPECS.md)

### Still open (documented gaps)

These cannot be signed off from documentation alone today:

| Gap | Status |
|-----|--------|
| Support / LTS policy | Pre-1.0 — [SUPPORT.md](SUPPORT.md) |
| Performance benchmarks | Planned 0.9 — [ROADMAP](ROADMAP.md) |
| Production case study | Planned 1.0 |
| MySQL / Oracle / SQL Server certification | Not CI-tested |
| SOC2 / HIPAA / FedRAMP mapping | Not certified — [compliance](guides/compliance.md) |

---

## Summary

| Question | Answer from docs |
|----------|------------------|
| What does it do? | SQL-first semantic CRUD + optional RDF/FastAPI |
| Why use it? | Legacy SQL + ontology APIs, hybrid graph, content negotiation |
| Production ready? | **No** — 0.5.x beta |
| Actively maintained? | Yes (OSS); no commercial SLA |
| Migration difficulty? | Moderate–high; 0.4→0.5 documented |
| Onboarding difficulty? | Moderate |
| Risks? | Technical risks documented; enterprise/compliance gaps remain |

**Read next:** [SUPPORT.md](SUPPORT.md) · [Compliance](guides/compliance.md) · [Security](SECURITY.md) · [Compatibility](COMPATIBILITY.md)
