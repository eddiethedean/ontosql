"""Optional JSON-LD compaction and framing (requires PyLD)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


class UnsafeJsonLdContextError(ValueError):
    """Raised when JSON-LD processing would fetch a remote context URL."""


def _require_pyld() -> Any:
    try:
        import pyld.jsonld as jsonld
    except ImportError as exc:
        raise ImportError(
            "JSON-LD compaction requires the jsonld extra: pip install ontosql[jsonld]"
        ) from exc
    return jsonld


def _is_remote_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https", "ftp")


def safe_document_loader(url: str, options: dict[str, Any]) -> dict[str, Any]:
    """PyLD document loader that blocks remote URL fetches (SSRF mitigation)."""
    if _is_remote_url(url):
        raise UnsafeJsonLdContextError(
            f"Remote JSON-LD context fetch blocked for {url!r}; "
            "pass allow_remote_contexts=True with a custom document_loader to opt in"
        )
    raise UnsafeJsonLdContextError(
        f"JSON-LD context {url!r} is not available locally; provide a custom document_loader"
    )


def compact_jsonld(
    document: dict[str, Any],
    context: dict[str, Any] | list[Any],
    *,
    document_loader: Any | None = None,
    allow_remote_contexts: bool = False,
) -> dict[str, Any]:
    """Compact a JSON-LD document with the given context."""
    jsonld = _require_pyld()
    loader = document_loader
    if loader is None and not allow_remote_contexts:
        loader = safe_document_loader
    options: dict[str, Any] = {}
    if loader is not None:
        options["documentLoader"] = loader
    return jsonld.compact(document, context, options=options)


def frame_jsonld(
    document: dict[str, Any],
    frame: dict[str, Any],
    *,
    document_loader: Any | None = None,
    allow_remote_contexts: bool = False,
) -> dict[str, Any]:
    """Frame a JSON-LD document."""
    jsonld = _require_pyld()
    loader = document_loader
    if loader is None and not allow_remote_contexts:
        loader = safe_document_loader
    options: dict[str, Any] = {}
    if loader is not None:
        options["documentLoader"] = loader
    return jsonld.frame(document, frame, options=options)
