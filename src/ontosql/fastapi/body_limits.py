"""Request body size and JSON depth limits for FastAPI routes."""

from __future__ import annotations

import json

from fastapi import HTTPException, Request, status

DEFAULT_MAX_BODY_BYTES = 64 * 1024
DEFAULT_MAX_JSON_DEPTH = 64

_HTTP_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)


def json_nesting_depth(raw: bytes, *, limit: int = DEFAULT_MAX_JSON_DEPTH) -> int:
    """Estimate max nesting depth of JSON brackets in raw bytes."""
    depth = 0
    max_depth = 0
    in_string = False
    escape = False
    for byte in raw:
        ch = chr(byte)
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in "{[":
            depth += 1
            max_depth = max(max_depth, depth)
            if max_depth > limit:
                return max_depth
        elif ch in "}]":
            depth = max(depth - 1, 0)
    return max_depth


async def read_json_body(
    request: Request,
    *,
    max_bytes: int = DEFAULT_MAX_BODY_BYTES,
    max_depth: int = DEFAULT_MAX_JSON_DEPTH,
) -> dict:
    """Read and parse JSON request body with size and depth limits."""
    raw = await request.body()
    if len(raw) > max_bytes:
        raise HTTPException(status_code=_HTTP_413, detail="Request body too large")
    if json_nesting_depth(raw, limit=max_depth) > max_depth:
        raise HTTPException(status_code=400, detail="JSON nesting too deep")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    return data
