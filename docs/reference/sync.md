# Sync API

Graph sync and materialization. See [HYBRID.md](../HYBRID.md) and [graph sync operations](../guides/graph-sync-operations.md).

## Targets

::: ontosql.sync.StoreSyncTarget

::: ontosql.sync.target.GraphSyncTarget

## Push and remove

::: ontosql.sync.push_instance

::: ontosql.sync.remove_instance

## Materialize from SQL

::: ontosql.sync.materialize.materialize_find

::: ontosql.sync.materialize.materialize_find_async

## Graph sync mode

::: ontosql.sync.graph.GraphSyncMode

## Session integration

Graph sync is configured on `OntoSession` / `AsyncOntoSession` via `graph_sync=` — see [Session API](session.md).

Errors: `GraphSyncError`, `GraphSyncFailure` — [session reference](session.md).
