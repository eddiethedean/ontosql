"""Shared RDF literal read/write helpers."""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin

from pyoxigraph import Literal, NamedNode

from ontosql.registry import PrefixRegistry


class LiteralCoercionError(Exception):
    """Raised when an RDF literal cannot be coerced to a Python value."""


def expand_datatype(meta: dict[str, Any], registry: PrefixRegistry) -> str | None:
    datatype = meta.get("datatype")
    if datatype is None:
        return None
    if ":" in datatype and "://" not in datatype:
        return registry.expand(datatype)
    return datatype


def literal_matches_meta(term: Literal, meta: dict[str, Any], registry: PrefixRegistry) -> bool:
    language = meta.get("language")
    if language is not None:
        return term.language == language
    datatype = expand_datatype(meta, registry)
    if datatype is not None:
        return term.datatype is not None and str(term.datatype) == datatype
    return True


def pick_literal(
    objects: list[Any],
    meta: dict[str, Any],
    registry: PrefixRegistry,
    *,
    error_type: type[Exception] = LiteralCoercionError,
) -> Any:
    literals = [o for o in objects if isinstance(o, Literal)]
    if not literals:
        return objects[0]
    if meta.get("language") or meta.get("datatype"):
        for lit in literals:
            if literal_matches_meta(lit, meta, registry):
                return lit
        raise error_type(
            f"No literal matches expected metadata language={meta.get('language')!r} "
            f"datatype={meta.get('datatype')!r}"
        )
    return literals[0]


def scalar_type(py_type: Any) -> Any:
    """Unwrap Optional[T] / Union[T, None] to T for coercion."""
    origin = get_origin(py_type)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(py_type) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return py_type


def coerce_literal(
    term: Any,
    *,
    py_type: Any,
    registry: PrefixRegistry,
    meta: dict[str, Any],
    error_type: type[Exception] = LiteralCoercionError,
) -> Any:
    if isinstance(term, NamedNode):
        return str(term)
    if not isinstance(term, Literal):
        return str(term)
    raw = str(term.value)
    scalar = scalar_type(py_type)
    if scalar is bool:
        lowered = raw.lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
        raise error_type(f"Cannot coerce literal {raw!r} to bool")
    if scalar is int:
        try:
            return int(raw)
        except ValueError as exc:
            raise error_type(f"Cannot coerce literal {raw!r} to int") from exc
    if scalar is float:
        try:
            return float(raw)
        except ValueError as exc:
            raise error_type(f"Cannot coerce literal {raw!r} to float") from exc
    expected_dt = expand_datatype(meta, registry)
    if expected_dt is not None and term.datatype is not None and str(term.datatype) != expected_dt:
        raise error_type(
            f"Literal datatype {term.datatype!s} does not match expected {expected_dt!r}"
        )
    return raw


def literal_object(
    value: Any,
    *,
    registry: PrefixRegistry,
    meta: dict[str, Any] | None = None,
) -> Literal | NamedNode:
    if isinstance(value, str) and ("://" in value or value.startswith("urn:")):
        return NamedNode(value)
    if isinstance(value, bool):
        return Literal(value)
    datatype = meta.get("datatype") if meta else None
    language = meta.get("language") if meta else None
    if datatype is not None:
        is_curie = ":" in datatype and "://" not in datatype
        dt_iri = registry.expand(datatype) if is_curie else datatype
        return Literal(str(value), datatype=NamedNode(dt_iri))
    if language is not None:
        return Literal(str(value), language=language)
    return Literal(str(value))
