"""FastAPI response classes for semantic formats."""

from __future__ import annotations

import json
from typing import Any

from fastapi.responses import Response

from ontosql.export._formats import media_type_for_format, normalize_format


def _dumps_json(data: Any) -> str:
    """Serialize data to a JSON string, using orjson when available."""
    try:
        import orjson
    except ImportError:
        return json.dumps(data, indent=2)

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()


def _serialize_data(data: Any, fmt: str) -> tuple[str, str]:
    """Return (body, media_type) for export-capable instance or pre-built payload."""
    rdf_fmt = normalize_format(fmt)

    if rdf_fmt == "json-ld":
        if hasattr(data, "to_jsonld") and callable(data.to_jsonld):
            body = _dumps_json(data.to_jsonld())
            return body, "application/ld+json"
        if isinstance(data, dict):
            return _dumps_json(data), "application/ld+json"

    if hasattr(data, "to_rdf") and callable(data.to_rdf):
        body = data.to_rdf(format=rdf_fmt)
        return body, media_type_for_format(rdf_fmt)

    if isinstance(data, str):
        return data, media_type_for_format(rdf_fmt)

    raise TypeError(
        "Response data must support to_jsonld/to_rdf, be a JSON-LD dict, or an RDF string"
    )


class RDFResponse(Response):
    """RDF serialization response (turtle, n-triples, rdf+xml, json-ld)."""

    def __init__(
        self,
        content: Any,
        *,
        format: str = "turtle",
        status_code: int = 200,
        **kwargs: Any,
    ) -> None:
        body, media_type = _serialize_data(content, format)
        super().__init__(content=body, media_type=media_type, status_code=status_code, **kwargs)


class JSONLDResponse(RDFResponse):
    """JSON-LD response (application/ld+json)."""

    def __init__(self, content: Any, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content, format="json-ld", status_code=status_code, **kwargs)


class TurtleResponse(RDFResponse):
    def __init__(self, content: Any, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content, format="turtle", status_code=status_code, **kwargs)


class NTriplesResponse(RDFResponse):
    def __init__(self, content: Any, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content, format="nt", status_code=status_code, **kwargs)


class RDFXMLResponse(RDFResponse):
    def __init__(self, content: Any, status_code: int = 200, **kwargs: Any) -> None:
        super().__init__(content, format="xml", status_code=status_code, **kwargs)
