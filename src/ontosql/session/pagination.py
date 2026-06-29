"""Pagination helpers for OntoSQL sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ontosql.semantic.model import OntoModel

T = TypeVar("T", bound=OntoModel)


@dataclass
class Page(Generic[T]):
    """Paginated query result."""

    items: list[T]
    total: int | None
    limit: int
    offset: int


def _build_page(
    items: list[T],
    *,
    total: int | None,
    limit: int,
    offset: int,
) -> Page[T]:
    return Page(items=items, total=total, limit=limit, offset=offset)


def paginate(
    session: Any,
    entity_type: type[T],
    *,
    where: Any | None = None,
    order_by: Any | None = None,
    limit: int = 20,
    offset: int = 0,
    include_total: bool = True,
) -> Page[T]:
    """Return a page of entities from a synchronous OntoSession."""
    items = session.find(
        entity_type,
        where=where,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    total = session.count(entity_type, where=where) if include_total else None
    return _build_page(items, total=total, limit=limit, offset=offset)


async def paginate_async(
    session: Any,
    entity_type: type[T],
    *,
    where: Any | None = None,
    order_by: Any | None = None,
    limit: int = 20,
    offset: int = 0,
    include_total: bool = True,
) -> Page[T]:
    """Return a page of entities from an AsyncOntoSession."""
    items = await session.find(
        entity_type,
        where=where,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    total = await session.count(entity_type, where=where) if include_total else None
    return _build_page(items, total=total, limit=limit, offset=offset)
