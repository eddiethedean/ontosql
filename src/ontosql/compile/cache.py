"""Cached select-plan skeletons per mapper."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from ontosql.compile.plan import ColumnProjection


def _label(table_name: str, field_name: str) -> str:
    return f"{table_name}_{field_name}"


@dataclass(frozen=True)
class NestedJoinSpec:
    """Static nested join metadata for a mapper."""

    nested_field: str
    nested_table: Any
    join: Any
    nested_mapper: type[Any]
    projections: tuple[ColumnProjection, ...]


@dataclass(frozen=True)
class SelectSkeleton:
    """Immutable SELECT structure for a mapper (filters applied separately)."""

    mapper_cls: type[Any]
    root_table: Any
    projections: tuple[ColumnProjection, ...]
    nested_joins: tuple[NestedJoinSpec, ...]
    select_columns: tuple[Any, ...]
    from_clause: Any


@lru_cache(maxsize=128)
def select_skeleton(mapper_cls: type[Any]) -> SelectSkeleton:
    """Build and cache the static portion of a SELECT for a mapper."""
    root_table = mapper_cls.primary_table
    if root_table is None:
        raise ValueError(f"Mapper {mapper_cls.__name__} has no primary_table")

    projections: list[ColumnProjection] = []
    nested_joins: list[NestedJoinSpec] = []
    columns: list[Any] = []

    for field_name, cmap in mapper_cls.column_maps.items():
        table_name = cmap.table_name
        label = _label(table_name, field_name)
        col = cmap.column.label(label)
        columns.append(col)
        projections.append(
            ColumnProjection(
                label=label,
                semantic_field=field_name,
                column=cmap.column,
                source="root",
            )
        )

    for field_name, cmap in mapper_cls.computed_maps.items():
        table_name = str(root_table.name)
        label = _label(f"{table_name}_computed", field_name)
        col = cmap.expression.label(label)
        columns.append(col)
        projections.append(
            ColumnProjection(
                label=label,
                semantic_field=field_name,
                column=cmap.expression,
                source="root",
            )
        )

    from_clause = root_table
    for nested_field, nmap in mapper_cls.nested_maps.items():
        nested_mapper = nmap.nested_mapper
        nested_table = nested_mapper.primary_table
        from_clause = from_clause.outerjoin(nested_table, nmap.join)  # type: ignore[union-attr]
        nested_projs: list[ColumnProjection] = []
        for nf_name, cmap in nested_mapper.column_maps.items():
            table_name = cmap.table_name
            label = _label(f"{nested_field}_{table_name}", nf_name)
            col = cmap.column.label(label)
            columns.append(col)
            nested_projs.append(
                ColumnProjection(
                    label=label,
                    semantic_field=nf_name,
                    column=cmap.column,
                    source=nested_field,
                )
            )
        nested_joins.append(
            NestedJoinSpec(
                nested_field=nested_field,
                nested_table=nested_table,
                join=nmap.join,
                nested_mapper=nested_mapper,
                projections=tuple(nested_projs),
            )
        )

    return SelectSkeleton(
        mapper_cls=mapper_cls,
        root_table=root_table,
        projections=tuple(projections),
        nested_joins=tuple(nested_joins),
        select_columns=tuple(columns),
        from_clause=from_clause,
    )


def skeleton_to_plan_parts(
    skeleton: SelectSkeleton,
) -> tuple[
    list[ColumnProjection],
    dict[str, list[ColumnProjection]],
    list[Any],
    Any,
]:
    """Expand a skeleton into mutable plan building blocks."""
    projections = list(skeleton.projections)
    nested_projections: dict[str, list[ColumnProjection]] = {
        spec.nested_field: list(spec.projections) for spec in skeleton.nested_joins
    }
    return projections, nested_projections, list(skeleton.select_columns), skeleton.from_clause
