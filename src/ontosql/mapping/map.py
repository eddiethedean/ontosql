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
class ComputedMap:
    """Maps a read-only semantic field to a SQL expression."""

    semantic_field: str
    expression: ColumnElement[Any]
    property_curie: str | None = None


@dataclass(frozen=True)
class CollectionMap:
    """Maps a semantic list field to related entities via a bridge table."""

    semantic_field: str
    entity_type: type[Any]
    through: Any
    source_fk: ColumnElement[Any]
    target_fk: ColumnElement[Any]
    nested_mapper: type[Any]
    property_curie: str | None = None
    cascade: CascadePolicy = CascadePolicy.LINK

    @property
    def through_table(self) -> Any:
        if hasattr(self.through, "__table__"):
            return self.through.__table__
        return self.through


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


def _column_field_name(col: ColumnElement[Any]) -> str:
    key = getattr(col, "key", None)
    if key:
        return str(key)
    name = getattr(col, "name", None)
    if name:
        return str(name)
    raise ValueError(f"Cannot infer semantic field name for column {col!r}")


def _guess_nested_field(entity_type: type[Any]) -> str:
    return entity_type.__name__[0].lower() + entity_type.__name__[1:]


def column(
    col: ColumnElement[Any],
    *,
    property: str | None = None,
    field: str | None = None,
) -> ColumnMap:
    """Map a semantic field to a SQL column (preferred over ``Map(...)``)."""
    name = field or _column_field_name(col)
    return ColumnMap(semantic_field=name, column=col, property_curie=property)


def nested(
    entity_type: type[Any],
    *,
    join: ColumnElement[bool],
    nested_map: type[Any],
    property: str | None = None,
    field: str | None = None,
    target: Any = None,  # noqa: ARG001 — accepted for API compatibility with docs
    cascade: CascadePolicy = CascadePolicy.LINK,
    fk_column: ColumnElement[Any] | None = None,
) -> NestedMap:
    """Map a nested semantic entity (preferred over ``Map.nested``)."""
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


def computed(
    expression: ColumnElement[Any],
    *,
    field: str,
    property: str | None = None,
) -> ComputedMap:
    """Map a read-only computed field (preferred over ``Map.computed``)."""
    return ComputedMap(
        semantic_field=field,
        expression=expression,
        property_curie=property,
    )


def collection(
    entity_type: type[Any],
    *,
    through: Any,
    source_fk: ColumnElement[Any],
    target_fk: ColumnElement[Any],
    nested_map: type[Any],
    property: str | None = None,
    field: str | None = None,
    cascade: CascadePolicy = CascadePolicy.LINK,
) -> CollectionMap:
    """Map a many-to-many collection (preferred over ``Map.collection``)."""
    name = field or f"{_guess_nested_field(entity_type)}s"
    return CollectionMap(
        semantic_field=name,
        entity_type=entity_type,
        through=through,
        source_fk=source_fk,
        target_fk=target_fk,
        nested_mapper=nested_map,
        property_curie=property,
        cascade=cascade,
    )


class Map:
    """Factory for column and nested map bindings (delegates to module functions)."""

    def __new__(
        cls,
        col: ColumnElement[Any],
        *,
        property: str | None = None,
        field: str | None = None,
    ) -> ColumnMap:
        return column(col, property=property, field=field)

    @staticmethod
    def nested(
        entity_type: type[Any],
        *,
        join: ColumnElement[bool],
        nested_map: type[Any],
        property: str | None = None,
        field: str | None = None,
        target: Any = None,
        cascade: CascadePolicy = CascadePolicy.LINK,
        fk_column: ColumnElement[Any] | None = None,
    ) -> NestedMap:
        return nested(
            entity_type,
            join=join,
            nested_map=nested_map,
            property=property,
            field=field,
            target=target,
            cascade=cascade,
            fk_column=fk_column,
        )

    @staticmethod
    def computed(
        expression: ColumnElement[Any],
        *,
        field: str,
        property: str | None = None,
    ) -> ComputedMap:
        return computed(expression, field=field, property=property)

    @staticmethod
    def collection(
        entity_type: type[Any],
        *,
        through: Any,
        source_fk: ColumnElement[Any],
        target_fk: ColumnElement[Any],
        nested_map: type[Any],
        property: str | None = None,
        field: str | None = None,
        cascade: CascadePolicy = CascadePolicy.LINK,
    ) -> CollectionMap:
        return collection(
            entity_type,
            through=through,
            source_fk=source_fk,
            target_fk=target_fk,
            nested_map=nested_map,
            property=property,
            field=field,
            cascade=cascade,
        )
