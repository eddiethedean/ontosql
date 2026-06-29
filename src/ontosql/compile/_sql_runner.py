"""Shared SQL execution helpers for sync and async compile paths."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select, update

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.write import _column_key, count_scalar


class ExecuteError(Exception):
    """Raised when a write/delete plan cannot be executed safely."""


def _apply_where(stmt: Any, table: Any, where: dict[str, Any]) -> Any:
    for col_name, value in where.items():
        stmt = stmt.where(table.c[col_name] == value)
    return stmt


def nested_delete_fk_nulling(plan: WritePlan) -> dict[str, Any]:
    """FK columns to null before nested deletes (empty when not applicable)."""
    if not plan.nested_deletes or plan.root.where is None:
        return {}
    fk_nulling: dict[str, Any] = {}
    for field_name, _ in plan.nested_deletes:
        nmap = plan.mapper_cls.nested_maps.get(field_name)
        if nmap is None or nmap.fk_column is None:
            continue
        fk_nulling[_column_key(nmap.fk_column)] = None
    return fk_nulling


def run_null_fks_for_nested_deletes(
    plan: WritePlan,
    *,
    run: Callable[[Any], Any],
) -> None:
    fk_nulling = nested_delete_fk_nulling(plan)
    if not fk_nulling or plan.root.where is None:
        return
    table = plan.root.table
    stmt = update(table).values(**fk_nulling)
    stmt = _apply_where(stmt, table, plan.root.where)
    run(stmt)


def nested_delete_identity(delete_plan: DeletePlan) -> Any:
    if delete_plan.root.where is None:
        raise ExecuteError("nested delete plan requires where clause")
    return next(iter(delete_plan.root.where.values()))


def check_replace_nested_exclusive(count: int, field_name: str, nested_id: Any) -> None:
    if count > 0:
        raise ExecuteError(
            f"Cannot REPLACE nested {field_name!r}: nested identity {nested_id!r} "
            f"is still referenced by {count} other row(s)"
        )


def inbound_fk_count_stmts(
    mapper_registry: Any,
    delete_plan: DeletePlan,
    *,
    exclude_table: Any | None = None,
    exclude_where: dict[str, Any] | None = None,
) -> list[tuple[str, Any]]:
    """Build COUNT statements for inbound FK references to a nested row across all mappers."""
    nested_mapper = delete_plan.mapper_cls
    nested_entity = nested_mapper.entity
    nested_id = nested_delete_identity(delete_plan)
    stmts: list[tuple[str, Any]] = []
    for mapper_cls in mapper_registry.all_mappers():
        for nmap in mapper_cls.nested_maps.values():
            if nmap.nested_mapper.entity != nested_entity or nmap.fk_column is None:
                continue
            fk_key = _column_key(nmap.fk_column)
            parent_table = mapper_cls.primary_table
            if parent_table is None:
                continue
            stmt = (
                select(func.count())
                .select_from(parent_table)
                .where(parent_table.c[fk_key] == nested_id)
            )
            if (
                exclude_where is not None
                and exclude_table is not None
                and parent_table == exclude_table
            ):
                identity_col = mapper_cls.column_maps[mapper_cls.identity_field]
                parent_id_key = _column_key(identity_col.column)
                parent_id = exclude_where.get(parent_id_key)
                if parent_id is not None:
                    stmt = stmt.where(parent_table.c[parent_id_key] != parent_id)
            label = f"{mapper_cls.__name__}.{nmap.semantic_field}"
            stmts.append((label, stmt))
        for cmap in mapper_cls.collection_maps.values():
            if cmap.nested_mapper.entity != nested_entity:
                continue
            through_table = cmap.through_table
            target_key = _column_key(cmap.target_fk)
            stmt = (
                select(func.count())
                .select_from(through_table)
                .where(through_table.c[target_key] == nested_id)
            )
            label = f"{mapper_cls.__name__}.{cmap.semantic_field}"
            stmts.append((label, stmt))
    return stmts


def assert_replace_nested_exclusive(
    plan: WritePlan,
    field_name: str,
    delete_plan: DeletePlan,
    *,
    run_count: Callable[[Any], Any],
    mapper_registry: Any | None = None,
) -> None:
    nested_id = nested_delete_identity(delete_plan)
    if mapper_registry is None:
        raise ExecuteError(
            "REPLACE nested delete requires mapper_registry= for cross-table FK safety"
        )
    stmts = inbound_fk_count_stmts(
        mapper_registry,
        delete_plan,
        exclude_table=plan.root.table,
        exclude_where=plan.root.where,
    )
    total = sum(count_scalar(run_count(stmt)) for _, stmt in stmts)
    check_replace_nested_exclusive(total, field_name, nested_id)
