"""Unified content negotiation for instance and graph responses."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import Response
from triplemodel import Store

from ontosql.fastapi.negotiate import (
    negotiate_graph_response,
    negotiate_onto_response,
    parse_accept_mime,
)
from ontosql.semantic.model import OntoModel


def serialize_response(
    request: Request,
    data: OntoModel | list[OntoModel] | Store | dict[str, Any],
    *,
    jsonld_context: dict[str, Any] | None = None,
) -> Response:
    """Pick serialization backend based on data type and Accept header."""
    if isinstance(data, Store):
        chosen = parse_accept_mime(request.headers.get("accept"))
        if chosen is None:
            chosen = "text/turtle"
        return negotiate_graph_response(chosen, data)
    payload = data
    if jsonld_context is not None and isinstance(payload, dict):
        payload = {**payload, "@context": jsonld_context}
    return negotiate_onto_response(request, payload)
