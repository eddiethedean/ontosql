"""Column key utilities for SQL compile."""

from __future__ import annotations

from typing import Any

from ontosql.compile.errors import WriteCompileError


def count_scalar(row: Any) -> int:
    if hasattr(row, "_mapping"):
        return int(next(iter(row._mapping.values())))
    if isinstance(row, tuple):
        return int(row[0])
    return int(row)


def column_key(column: Any) -> str:
    key = getattr(column, "key", None)
    if key:
        return str(key)
    name = getattr(column, "name", None)
    if name:
        return str(name)
    raise WriteCompileError(f"Cannot resolve column key for {column!r}")
