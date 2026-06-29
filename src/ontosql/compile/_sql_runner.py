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


def replace_nested_exclusive_count_stmt(
    plan: WritePlan,
    field_name: str,
    delete_plan: DeletePlan,
) -> Any | None:
    """Build a COUNT stmt for REPLACE exclusivity, or None when check does not apply."""
    nmap = plan.mapper_cls.nested_maps.get(field_name)
    if nmap is None or nmap.fk_column is None or plan.root.where is None:
        return None
    nested_id = nested_delete_identity(delete_plan)
    fk_key = _column_key(nmap.fk_column)
    parent_table = plan.root.table
    identity_col = plan.mapper_cls.column_maps[plan.mapper_cls.identity_field]
    parent_id_key = _column_key(identity_col.column)
    parent_id = plan.root.where.get(parent_id_key)
    stmt = select(func.count()).select_from(parent_table).where(parent_table.c[fk_key] == nested_id)
    if parent_id is not None:
        stmt = stmt.where(parent_table.c[parent_id_key] != parent_id)
    return stmt


def check_replace_nested_exclusive(count: int, field_name: str, nested_id: Any) -> None:
    if count > 0:
        raise ExecuteError(
            f"Cannot REPLACE nested {field_name!r}: nested identity {nested_id!r} "
            f"is still referenced by {count} other row(s)"
        )


def assert_replace_nested_exclusive(
    plan: WritePlan,
    field_name: str,
    delete_plan: DeletePlan,
    *,
    run_count: Callable[[Any], Any],
) -> None:
    stmt = replace_nested_exclusive_count_stmt(plan, field_name, delete_plan)
    if stmt is None:
        return
    nested_id = nested_delete_identity(delete_plan)
    count = count_scalar(run_count(stmt))
    check_replace_nested_exclusive(count, field_name, nested_id)
