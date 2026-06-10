"""Optional JSON-LD compaction and framing (requires PyLD)."""

from __future__ import annotations

from typing import Any


def _require_pyld() -> Any:
    try:
        import pyld.jsonld as jsonld
    except ImportError as exc:
        raise ImportError(
            "JSON-LD compaction requires the jsonld extra: pip install ontosql[jsonld]"
        ) from exc
    return jsonld


def compact_jsonld(document: dict[str, Any], context: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Compact a JSON-LD document with the given context."""
    jsonld = _require_pyld()
    return jsonld.compact(document, context)


def frame_jsonld(document: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    """Frame a JSON-LD document."""
    jsonld = _require_pyld()
    return jsonld.frame(document, frame)
