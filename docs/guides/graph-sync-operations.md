# Graph sync operations runbook

Operational guide for **hybrid SQL + RDF** deployments using `graph_sync`. Architecture and API: [HYBRID.md](../HYBRID.md).

!!! danger "Not two-phase commit"
    SQL commits **before** graph sync runs. Failed graph sync leaves **split-brain** — SQL durable, graph partial or stale.

## When this applies

You configured:

```python
OntoSession(..., graph_sync=target, graph_sync_mode="replace")
```

Graph updates queue on `save()` / `delete()` and flush **after SQL commit** when the session context exits.

## Failure modes

| Symptom | Cause | SQL state | Graph state |
|---------|-------|-----------|-------------|
| `GraphSyncError` on exit | Remote graph down, auth failure, network | **Committed** | Partial or unchanged |
| `session.graph_sync_pending` non-empty after error | Queue preserved for retry | Committed | Behind SQL |
| Graph empty mid-request | Sync runs at commit, not on `save()` | In transaction | Not updated yet |
| Rolled-back session | Exception before exit | Rolled back | Queue discarded |

## Immediate response (on-call)

1. **Confirm SQL succeeded** — treat SQL as source of truth
2. **Inspect failures:**

   ```python
   session.graph_sync_failures  # list of GraphSyncFailure
   session.graph_sync_pending   # remaining queue
   ```

3. **Fix graph target** — credentials, network, SparqlModel store health
4. **Retry:**

   ```python
   session.retry_graph_sync()
   ```

5. If retry fails repeatedly, **disable hot-path sync** and switch to batch reconcile (below)

## Monitoring recommendations

| Signal | Alert when |
|--------|------------|
| `GraphSyncError` in logs | Any occurrence in production |
| `graph_sync_pending` after request | Non-empty after handler completes |
| Graph lag vs SQL row count | Nightly reconcile diff &gt; threshold |
| Graph store error rate | SparqlModel / HTTP endpoint 5xx |

OntoSQL 0.5.x provides basic `ontosql` logger hooks at commit/sync boundaries. Structured logging and OpenTelemetry are **planned 0.7** — [ROADMAP.md](../ROADMAP.md).

## Reconciliation patterns

Pick one for production — do not rely on in-process sync alone at scale.

### Outbox table (recommended for high reliability)

1. In same SQL transaction as business write, insert row into `graph_outbox(entity_type, identity, op)`
2. Commit SQL
3. Worker reads outbox, calls `push_instance` / `remove_instance`, marks done
4. Retry with backoff; dead-letter after N failures

OntoSQL does not ship an outbox implementation — integrate in your app.

### Nightly reconcile

```python
from ontosql.sync import materialize_find

# Build graph from SQL truth
graph = materialize_find(session, Person, limit=...)
# Diff against remote store; repair deltas
```

Schedule off-peak; alert on diff size.

### Batch-only (disable hot-path sync)

Remove `graph_sync` from request path. Export jobs push to graph on schedule. Simplest ops; higher staleness.

## Preventing split-brain

| Practice | Why |
|----------|-----|
| Never assume graph is current inside `with session` before exit | Sync is post-commit |
| Use `LINK` not `REPLACE` for shared nested entities | Avoids SQL/graph delete conflicts |
| Authenticate graph endpoint | Prevents unauthorized graph mutation |
| Idempotent push modes | `replace` vs `patch` — document team choice in [HYBRID.md](../HYBRID.md) |

## Testing before production

- [ ] Inject graph failure after SQL commit; verify `GraphSyncError` and queue preservation
- [ ] Verify `retry_graph_sync()` succeeds after fix
- [ ] Load test graph target independently of SQL
- See [testing guide](testing.md)

## Escalation

- Application team owns outbox/reconcile architecture
- OntoSQL library: file [GitHub issue](https://github.com/eddiethedean/ontosql/issues) with reproduction
- Security: [SECURITY.md](../SECURITY.md)

## Related

- [HYBRID.md](../HYBRID.md)
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md#graphsyncerror-after-commit)
- [enterprise adoption](../enterprise-adoption.md)
