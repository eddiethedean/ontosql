# FastAPI API

Requires `pip install ontosql[fastapi]`. Beta-experimental tier — see [SPECS.md](../SPECS.md). **Not safe on public networks without auth** — [SECURITY.md](../SECURITY.md).

## OntoRouter

::: ontosql.fastapi.router.OntoRouter

::: ontosql.fastapi.router.DEFAULT_MAX_BODY_BYTES

## Lifespan and dependencies

::: ontosql.fastapi.deps.onto_async_session_lifespan

::: ontosql.fastapi.deps.onto_session_lifespan

::: ontosql.fastapi.deps.AsyncSessionDep

::: ontosql.fastapi.deps.SessionDep

::: ontosql.fastapi.deps.get_async_onto_session

::: ontosql.fastapi.deps.get_onto_session

## Content negotiation

::: ontosql.fastapi.negotiate.negotiate_onto_response

## RDF responses

::: ontosql.fastapi.responses.JSONLDResponse

::: ontosql.fastapi.responses.TurtleResponse

::: ontosql.fastapi.responses.NTriplesResponse

::: ontosql.fastapi.responses.RDFXMLResponse

::: ontosql.fastapi.responses.RDFResponse

## OpenAPI helpers

::: ontosql.fastapi.openapi.enrich_openapi_schema

::: ontosql.fastapi.openapi.install_onto_openapi

## Production patterns

List `GET` routes default to **`application/ld+json`** when no `Accept` header is sent (same as item `GET`). Pass `Accept: application/json` for a plain JSON array.

See [production-router.md](../guides/production-router.md) and [FastAPI quick start](../guides/fastapi-quickstart.md).
