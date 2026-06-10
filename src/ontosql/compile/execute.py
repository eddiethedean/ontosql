"""Execute compiled write and delete plans against SQLAlchemy."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.write import _column_key


class ExecuteError(Exception):
    """Raised when a write/delete plan cannot be executed safely."""


def _apply_where(stmt: Any, table: Any, where: dict[str, Any]) -> Any:
    for col_name, value in where.items():
        stmt = stmt.where(table.c[col_name] == value)
    return stmt


def _inserted_identity(result: Any, plan: WritePlan, values: dict[str, Any]) -> Any:
    identity_col = plan.mapper_cls.identity_field
    identity_key = None
    if identity_col in plan.mapper_cls.column_maps:
        col = plan.mapper_cls.column_maps[identity_col].column
        identity_key = getattr(col, "key", None) or getattr(col, "name", identity_col)
    if identity_key and identity_key in values and values[identity_key] is not None:
        return values[identity_key]
    if hasattr(result, "inserted_primary_key") and result.inserted_primary_key:
        return result.inserted_primary_key[0]
    return values.get(identity_key) if identity_key else None


def _apply_nested_fk_updates(
    plan: WritePlan,
    fk_updates: dict[str, Any],
    field_name: str,
    nested_id: Any,
) -> None:
    if nested_id is None:
        return
    nmap = plan.mapper_cls.nested_maps.get(field_name)
    if nmap is None or nmap.fk_column is None:
        return
    fk_updates[_column_key(nmap.fk_column)] = nested_id


def _update_identity(plan: WritePlan) -> Any:
    if plan.root.where is None:
        return None
    identity_col = plan.mapper_cls.identity_field
    identity_key = identity_col
    if identity_col in plan.mapper_cls.column_maps:
        col = plan.mapper_cls.column_maps[identity_col].column
        identity_key = getattr(col, "key", None) or getattr(col, "name", identity_col)
    return plan.root.where.get(str(identity_key))


def execute_write_plan(session: Any, plan: WritePlan) -> Any:
    """Execute a WritePlan synchronously; returns root identity value after insert."""
    fk_updates = dict(plan.fk_updates)
    for field_name, nested in plan.nested:
        nested_id = execute_write_plan(session, nested)
        _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

    table = plan.root.table
    values = dict(plan.root.values)
    values.update(fk_updates)

    if plan.operation == "insert":
        result = session.exec(insert(table).values(**values))
        return _inserted_identity(result, plan, values)

    if values:
        stmt = update(table).values(**values)
        if plan.root.where is not None:
            stmt = _apply_where(stmt, table, plan.root.where)
        session.exec(stmt)

    return _update_identity(plan)


def execute_delete_plan(session: Any, plan: DeletePlan) -> None:
    """Execute a DeletePlan synchronously."""
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    session.exec(stmt)


async def async_execute_write_plan(session: AsyncSession, plan: WritePlan) -> Any:
    """Execute a WritePlan on an AsyncSession."""
    fk_updates = dict(plan.fk_updates)
    for field_name, nested in plan.nested:
        nested_id = await async_execute_write_plan(session, nested)
        _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

    table = plan.root.table
    values = dict(plan.root.values)
    values.update(fk_updates)

    if plan.operation == "insert":
        result = await session.execute(insert(table).values(**values))
        return _inserted_identity(result, plan, values)

    if values:
        stmt = update(table).values(**values)
        if plan.root.where is not None:
            stmt = _apply_where(stmt, table, plan.root.where)
        await session.execute(stmt)

    return _update_identity(plan)


async def async_execute_delete_plan(session: AsyncSession, plan: DeletePlan) -> None:
    """Execute a DeletePlan on an AsyncSession."""
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)
