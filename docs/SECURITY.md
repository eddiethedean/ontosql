# Security

## SQL compilation

OntoSQL compiles semantic queries to SQLAlchemy statements with **bound parameters** for values in `where`, `save`, and `delete` plans. User-supplied filter values are passed as parameters, not interpolated into SQL strings.

Raw `sqlalchemy.text()` fragments are **rejected** in semantic `where` expressions (`CompileError`). Mapper-defined `ComputedMap.expression` and `NestedMap.join` remain trusted code — review mappers like schema migrations.

For ad hoc SQL, use the underlying SQLAlchemy session from your application layer with bound parameters — OntoSQL does not expose a raw SQL escape hatch on `OntoSession`.

## OntoRouter (FastAPI)

`OntoRouter` uses **async** `AsyncOntoSession` (`onto_async_session_lifespan` required). It is **not safe for public internet** without host-app controls:

| Control | Status |
|---------|--------|
| Authentication | **Not provided** — pass `dependencies=[Depends(your_auth)]` |
| Authorization | **Not provided** — object-level checks in your dependencies |
| Rate limiting | Not provided |
| Request body validation | Generated Pydantic models validate POST/PATCH bodies |
| Semantic validation | **Default `validate_entities=True`** runs `OntoModel.model_validate` |
| Body size cap | **Default `max_body_bytes=65536`** on POST/PATCH; streams body in chunks (413 when exceeded) |
| Async session | **Required** — `AsyncSessionDep` on all routes |

### Internet exposure requirements

Before mounting `OntoRouter` on a reachable host:

1. **Authentication** — add FastAPI `dependencies` on the router (see [production-router.md](guides/production-router.md#authentication-required)).
2. **Authorization** — verify the caller may access each `{entity_id}` and nested associations.
3. **Rate limits** — per client/API key at middleware or reverse proxy.
4. **Disable public `/docs`** in production or protect with auth.
5. **Reverse-proxy body limits** — complement router `max_body_bytes` with nginx/Envoy caps.

## RDF import limits

`import_from_rdf`, `load_graph`, and related helpers accept optional `max_bytes` and `max_triples` (raises `OntoImportError` when exceeded).

- Set **`untrusted=True`** on import paths that accept public payloads to apply `UNTRUSTED_DEFAULT_MAX_BYTES` (1 MiB) and `UNTRUSTED_DEFAULT_MAX_TRIPLES` (100k) when limits are omitted.
- **`max_triples` is checked after `graph.parse()`** — a small payload can still expand during parsing. Always set `max_bytes`, rate-limit import endpoints, and never expose import without authentication.
- **`max_nesting_depth`** (default 32) on `graph_to_instance` limits deep nested RDF chains during hydration.

**PyLD JSON-LD compaction** (`compact_jsonld`, `frame_jsonld`) uses a **safe document loader by default** that blocks remote `@context` URL fetches (SSRF mitigation). `allow_remote_contexts=True` requires an explicit trusted `document_loader=` (PyLD’s default loader fetches remote URLs). RDF import via pyoxigraph does not use PyLD.

## Graph sync consistency

When `graph_sync` is configured, graph updates are queued during `save()` / `delete()` and applied **after SQL commit**. If the session rolls back, queued graph updates are discarded.

If graph sync fails after commit, SQL remains committed and the queue is preserved for `retry_graph_sync()` — plan hybrid architectures with an outbox or reconcile job. See [HYBRID.md](HYBRID.md#graph-sync-failures-split-brain).

## REPLACE cascade

`CascadePolicy.REPLACE` deletes nested rows when associations change. It refuses to delete nested rows still referenced by other parent rows. Do not use REPLACE for shared entities.

See [guides/cascade-policies.md](guides/cascade-policies.md).

## Project governance

| Topic | Details |
|-------|---------|
| **License** | MIT |
| **Maintainers** | OntoSQL contributors — see [GitHub repository](https://github.com/eddiethedean/ontosql/graphs/contributors) |
| **Security contact** | [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories/new) (preferred) |
| **Support model** | Community best-effort — [SUPPORT.md](SUPPORT.md) |
| **Commercial support** | Not offered in 0.5.x |

## Vulnerability response

1. Report privately via GitHub Security Advisories or the security contact on the repository — **do not** open public issues for undisclosed vulnerabilities.
2. Maintainers acknowledge receipt when possible; **no published SLA** for triage or fix timelines in 0.5.x.
3. Fixes ship in patch/minor releases per severity; advisories published on GitHub when disclosed.
4. Enterprise teams should monitor [GitHub Advisories](https://github.com/eddiethedean/ontosql/security/advisories) and pin versions — [upgrading guide](guides/upgrading.md).

Pre-1.0: coordinate breaking security fixes with [CHANGELOG](changelog.md) and [SPECS](SPECS.md) stability tiers.

## Reporting vulnerabilities

Please report security issues privately via [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories/new). Do not open public issues for undisclosed vulnerabilities.
