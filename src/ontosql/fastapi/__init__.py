"""FastAPI integration (optional extra)."""

from __future__ import annotations

try:
    from ontosql.fastapi.deps import (
        AsyncSessionDep,
        SessionDep,
        get_async_onto_session,
        get_onto_session,
        onto_session_lifespan,
    )
    from ontosql.fastapi.negotiate import negotiate_onto_response
    from ontosql.fastapi.openapi import enrich_openapi_schema, install_onto_openapi
    from ontosql.fastapi.responses import (
        JSONLDResponse,
        NTriplesResponse,
        RDFResponse,
        RDFXMLResponse,
        TurtleResponse,
    )
    from ontosql.fastapi.router import OntoRouter
except ImportError as exc:
    if "fastapi" in str(exc).lower() or "starlette" in str(exc).lower():
        raise ImportError(
            "FastAPI support requires the fastapi extra: pip install ontosql[fastapi]"
        ) from exc
    raise

__all__ = [
    "AsyncSessionDep",
    "JSONLDResponse",
    "NTriplesResponse",
    "OntoRouter",
    "RDFResponse",
    "RDFXMLResponse",
    "SessionDep",
    "TurtleResponse",
    "enrich_openapi_schema",
    "get_async_onto_session",
    "get_onto_session",
    "install_onto_openapi",
    "negotiate_onto_response",
    "onto_async_session_lifespan",
    "onto_session_lifespan",
]
