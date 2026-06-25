"""Content negotiation for OntoSQL FastAPI routes."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from ontosql.fastapi.responses import (
    JSONLDResponse,
    NTriplesResponse,
    RDFXMLResponse,
    TurtleResponse,
)

# MIME type -> response factory
_ACCEPT_MAP: list[tuple[str, type[Response]]] = [
    ("application/ld+json", JSONLDResponse),
    ("text/turtle", TurtleResponse),
    ("application/n-triples", NTriplesResponse),
    ("application/rdf+xml", RDFXMLResponse),
]

_KNOWN_MIMES = frozenset(mime for mime, _ in _ACCEPT_MAP)


def _parse_accept_params(part: str) -> tuple[str, float]:
    """Parse one Accept entry into (media_type, q_value)."""
    tokens = [t.strip() for t in part.split(";") if t.strip()]
    if not tokens:
        return "", 1.0
    media_type = tokens[0].lower()
    q = 1.0
    for token in tokens[1:]:
        if token.startswith("q="):
            q_str = token[2:].strip()
            try:
                q = float(q_str)
            except ValueError:
                q = 1.0
    return media_type, q


def _matches_known_mime(media_type: str) -> str | None:
    """Return the known MIME if media_type matches exactly or as a type/* range."""
    if media_type in _KNOWN_MIMES:
        return media_type
    if "/" in media_type:
        major, _, _minor = media_type.partition("/")
        if _minor == "*" and major:
            matches = [m for m in _KNOWN_MIMES if m.startswith(f"{major}/")]
            if len(matches) == 1:
                return matches[0]
    return None


def _parse_accept(accept: str | None) -> str | None:
    """Return the best matching semantic media type from Accept header."""
    if not accept:
        return None
    candidates: list[tuple[float, str]] = []
    for part in accept.split(","):
        media_type, q = _parse_accept_params(part)
        if not media_type or q == 0.0:
            continue
        if media_type in ("*/*", "*"):
            continue
        matched = _matches_known_mime(media_type)
        if matched is not None:
            candidates.append((q, matched))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def parse_accept_mime(accept: str | None) -> str | None:
    """Public helper: best matching semantic MIME type from an Accept header."""
    return _parse_accept(accept)


def negotiate_onto_response(request: Request, data: Any) -> Response:
    """
    Return a FastAPI Response based on the request Accept header.

    Falls back to JSON-LD if data supports ``to_jsonld()``, otherwise JSON.
    """
    chosen = _parse_accept(request.headers.get("accept"))
    if chosen is None:
        if hasattr(data, "to_jsonld"):
            return JSONLDResponse(data)
        if isinstance(data, dict):
            return JSONLDResponse(data)
        return JSONResponse(content=data)

    for mime, response_cls in _ACCEPT_MAP:
        if mime == chosen:
            return response_cls(data)

    return JSONLDResponse(data)
