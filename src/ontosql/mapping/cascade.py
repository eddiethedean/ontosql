"""Nested save cascade policies."""

from __future__ import annotations

from enum import Enum


class CascadePolicy(str, Enum):
    """Explicit nested save behavior on Map.nested."""

    LINK = "link"
    UPSERT = "upsert"
    REPLACE = "replace"
    IGNORE = "ignore"
