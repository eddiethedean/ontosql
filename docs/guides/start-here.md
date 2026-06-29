# Start here

Pick the path that matches your goal. Each link is a single next step — not the full documentation map.

## SQL CRUD only (no RDF)

[Quick start](../getting-started/quickstart.md) — `pip install ontosql`, copy the Tier 1 script, run semantic CRUD in under 10 minutes (no repo clone).

**Then go deeper:** [Architecture](../ARCHITECTURE.md) · [Technical specification](../SPECS.md)

## Async sessions

[Async sessions](../getting-started/async.md) — `AsyncOntoSession` with the same API as sync; requires `ontosql[async]`.

## FastAPI production API

[Production FastAPI router](../guides/production-router.md) — auth, body limits, and async lifespan patterns.

**Example:** [person_org_api_production.py](https://github.com/eddiethedean/ontosql/blob/main/examples/person_org_api_production.py) in the repo (clone required).

## Hybrid SQL + RDF graph

[Hybrid deployments](../HYBRID.md) — mirror SQL writes to an RDF graph on commit; import and materialize.

Requires graph sync setup; eventually consistent after SQL commit.

## Nested writes and many-to-many

[Cascade policies](cascade-policies.md) — `link`, `upsert`, `replace`, `ignore` on nested entities.

[Bridge tables](bridge-tables.md) — `Map.collection` for many-to-many.

## Postgres in production

[Postgres dialect](postgres-dialect.md) — UUID, JSONB, ARRAY patterns.

## Evaluate for production

[Security](../SECURITY.md) · [Compatibility](../COMPATIBILITY.md) · [FAQ](../FAQ.md) · [Troubleshooting](../TROUBLESHOOTING.md)

!!! warning "OntoRouter on public networks"

    `OntoRouter` requires `dependencies=[Depends(your_auth)]` before internet exposure. See [production-router.md](production-router.md).

## Contribute to OntoSQL

[Contributing](../contributing.md) on this site · [CONTRIBUTING.md](https://github.com/eddiethedean/ontosql/blob/main/CONTRIBUTING.md) on GitHub

## Full documentation map

Return to the [documentation home](../index.md#documentation-map) for the complete table of contents.
