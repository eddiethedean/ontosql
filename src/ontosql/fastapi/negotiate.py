"""Content negotiation for OntoSQL FastAPI routes."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from triplemodel import Store

from ontosql.fastapi.responses import JSONLDResponse, RDFResponse
from ontosql.rdf.formats import format_for_mime, media_type_for_format

# MIME type -> RDF format key
_ACCEPT_FORMATS: list[tuple[str, str]] = [
    ("application/ld+json", "json-ld"),
    ("text/turtle", "turtle"),
    ("application/n-triples", "nt"),
    ("application/rdf+xml", "xml"),
]

_KNOWN_MIMES = frozenset(mime for mime, _ in _ACCEPT_FORMATS)
_JSON_MIME = "application/json"


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
                q_val = float(q_str)
            except ValueError:
                return media_type, -1.0
            if q_val < 0.0 or q_val > 1.0:
                return media_type, -1.0
            q = q_val
    return media_type, q


def _matches_known_mime(media_type: str) -> str | None:
    """Return the known MIME if media_type matches exactly or as a type/* range."""
    if media_type in _KNOWN_MIMES:
        return media_type
    if "/" in media_type:
        major, _, minor = media_type.partition("/")
        if minor == "*" and major:
            matches = [m for m in _KNOWN_MIMES if m.startswith(f"{major}/")]
            if len(matches) == 1:
                return matches[0]
            if major == "application" and "application/ld+json" in _KNOWN_MIMES:
                return "application/ld+json"
    return None


def _parse_accept(accept: str | None) -> str | None:
    """Return the best matching semantic media type from Accept header."""
    if not accept:
        return None
    candidates: list[tuple[float, str]] = []
    for part in accept.split(","):
        media_type, q = _parse_accept_params(part)
        if not media_type or q <= 0.0:
            continue
        if media_type in ("*/*", "*"):
            continue
        if media_type == _JSON_MIME:
            candidates.append((q, _JSON_MIME))
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


def negotiate_graph_response(chosen_mime: str, graph: Store) -> Response:
    """Serialize a TripleModel Store for a negotiated RDF MIME type."""
    fmt = format_for_mime(chosen_mime)
    if fmt is None:
        raise ValueError(f"Unsupported RDF MIME type: {chosen_mime!r}")
    body = graph.serialize(format=fmt)
    return Response(content=body, media_type=media_type_for_format(fmt))


def _json_response_for(data: Any) -> JSONResponse:
    if hasattr(data, "model_dump"):
        return JSONResponse(content=data.model_dump())
    if isinstance(data, list):
        body = [item.model_dump() if hasattr(item, "model_dump") else item for item in data]
        return JSONResponse(content=body)
    return JSONResponse(content=data)


def negotiate_onto_response(request: Request, data: Any) -> Response:
    """
    Return a FastAPI Response based on the request Accept header.

    Falls back to JSON-LD if data supports ``to_jsonld()``, otherwise JSON.
    """
    accept = request.headers.get("accept")
    chosen = _parse_accept(accept)
    if chosen == _JSON_MIME:
        return _json_response_for(data)

    if chosen is None:
        if hasattr(data, "to_jsonld"):
            return JSONLDResponse(data)
        if isinstance(data, dict):
            return JSONLDResponse(data)
        return JSONResponse(content=data)

    fmt = format_for_mime(chosen)
    if fmt is not None:
        try:
            return RDFResponse(data, format=fmt)
        except TypeError as exc:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=str(exc),
            ) from exc

    return JSONLDResponse(data)
