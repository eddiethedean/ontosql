"""Map descriptors binding semantic fields to SQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from ontosql.mapping.cascade import CascadePolicy


@dataclass(frozen=True)
class ColumnMap:
    """Maps a semantic field to a SQL column."""

    semantic_field: str
    column: ColumnElement[Any]
    property_curie: str | None = None

    @property
    def table_name(self) -> str:
        table = self.column.table
        if table is None:
            raise ValueError(f"Column {self.column!r} has no table")
        return str(table.name)


@dataclass(frozen=True)
class NestedMap:
    """Maps a semantic field to a nested entity via a join."""

    semantic_field: str
    entity_type: type[Any]
    join: ColumnElement[bool]
    nested_mapper: type[Any]
    property_curie: str | None = None
    cascade: CascadePolicy = CascadePolicy.LINK
    fk_column: ColumnElement[Any] | None = None

    @property
    def target_table(self) -> Any:
        """Table joined for the nested entity (from nested mapper root table)."""
        nested = self.nested_mapper
        if not hasattr(nested, "primary_table"):
            raise ValueError(f"Nested mapper {nested!r} has no primary_table")
        return nested.primary_table


class Map:
    """Factory for column and nested map bindings."""

    def __new__(
        cls,
        column: ColumnElement[Any],
        *,
        property: str | None = None,
        field: str | None = None,
    ) -> ColumnMap:
        name = field or _column_field_name(column)
        return ColumnMap(semantic_field=name, column=column, property_curie=property)

    @staticmethod
    def nested(
        entity_type: type[Any],
        *,
        join: ColumnElement[bool],
        nested_map: type[Any],
        property: str | None = None,
        field: str | None = None,
        target: Any = None,  # noqa: ARG004 — accepted for API compatibility with docs
        cascade: CascadePolicy = CascadePolicy.LINK,
        fk_column: ColumnElement[Any] | None = None,
    ) -> NestedMap:
        name = field or _guess_nested_field(entity_type)
        return NestedMap(
            semantic_field=name,
            entity_type=entity_type,
            join=join,
            nested_mapper=nested_map,
            property_curie=property,
            cascade=cascade,
            fk_column=fk_column,
        )


def _column_field_name(column: ColumnElement[Any]) -> str:
    key = getattr(column, "key", None)
    if key:
        return str(key)
    name = getattr(column, "name", None)
    if name:
        return str(name)
    raise ValueError(f"Cannot infer semantic field name for column {column!r}")


def _guess_nested_field(entity_type: type[Any]) -> str:
    return entity_type.__name__[0].lower() + entity_type.__name__[1:]
