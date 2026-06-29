"""Batch-load collection (many-to-many) fields."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ontosql.compile.cache import _label
from ontosql.compile.plan import ColumnProjection
from ontosql.semantic.model import OntoModel


def _column_key(column: Any) -> str:
    key = getattr(column, "key", None)
    if key:
        return str(key)
    name = getattr(column, "name", None)
    if name:
        return str(name)
    raise ValueError(f"Cannot resolve column key for {column!r}")


def compile_collection_load(
    mapper_cls: type[Any],
    collection_field: str,
    root_ids: list[Any],
) -> tuple[Any, list[ColumnProjection], str, str]:
    """Build a SELECT for collection members keyed by source FK.

    Returns (statement, nested_projections, source_key, target_key).
    """
    if not root_ids:
        raise ValueError("root_ids must not be empty")
    cmap = mapper_cls.collection_maps[collection_field]
    nested_mapper = cmap.nested_mapper
    nested_table = nested_mapper.primary_table
    through_table = cmap.through_table
    source_key = _column_key(cmap.source_fk)
    target_key = _column_key(cmap.target_fk)

    projections: list[ColumnProjection] = []
    columns: list[Any] = []
    source_label = _label("bridge", source_key)
    columns.append(cmap.source_fk.label(source_label))
    projections.append(
        ColumnProjection(
            label=source_label,
            semantic_field="_source_id",
            column=cmap.source_fk,
            source="bridge",
        )
    )

    for field_name, ncol in nested_mapper.column_maps.items():
        table_name = ncol.table_name
        label = _label(f"coll_{table_name}", field_name)
        col = ncol.column.label(label)
        columns.append(col)
        projections.append(
            ColumnProjection(
                label=label,
                semantic_field=field_name,
                column=ncol.column,
                source="nested",
            )
        )

    identity_col = nested_mapper.column_maps[nested_mapper.identity_field].column
    from_clause = through_table.join(nested_table, cmap.target_fk == identity_col)

    stmt = select(*columns).select_from(from_clause).where(cmap.source_fk.in_(root_ids))
    return stmt, projections, source_key, target_key


def hydrate_collection_row(
    projections: list[ColumnProjection],
    row: Any,
    nested_mapper: type[Any],
) -> OntoModel | None:
    """Build one nested entity from a collection load row."""
    from ontosql.session.hydrate import _row_get

    nested_entity = nested_mapper.entity
    nested_data: dict[str, Any] = {}
    any_value = False
    for proj in projections:
        if proj.semantic_field == "_source_id":
            continue
        val = _row_get(row, proj.label)
        nested_data[proj.semantic_field] = val
        if val is not None:
            any_value = True
    if not any_value:
        return None
    identity = nested_mapper.identity_field
    if nested_data.get(identity) is None:
        return None
    return nested_entity(**nested_data)


def group_collection_rows(
    mapper_cls: type[Any],
    collection_field: str,
    projections: list[ColumnProjection],
    rows: list[Any],
) -> dict[Any, list[OntoModel]]:
    """Group loaded collection rows by source root identity."""
    from ontosql.session.hydrate import _row_get

    cmap = mapper_cls.collection_maps[collection_field]
    nested_mapper = cmap.nested_mapper
    source_label = _label("bridge", _column_key(cmap.source_fk))
    grouped: dict[Any, list[OntoModel]] = {}
    for row in rows:
        source_id = _row_get(row, source_label)
        if source_id is None:
            continue
        item = hydrate_collection_row(projections, row, nested_mapper)
        if item is None:
            continue
        grouped.setdefault(source_id, []).append(item)
    return grouped
