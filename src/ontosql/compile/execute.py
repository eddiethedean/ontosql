"""Execute compiled write and delete plans against SQLAlchemy."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from ontosql.compile._sql_runner import (
    ExecuteError,
    _apply_where,
    assert_replace_nested_exclusive,
    nested_delete_fk_nulling,
    nested_delete_identity,
    run_null_fks_for_nested_deletes,
)
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.compile.write import _column_key, count_scalar
from ontosql.mapping.cascade import CascadePolicy


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


def _null_fks_for_nested_deletes(session: Any, plan: WritePlan) -> None:
    run_null_fks_for_nested_deletes(plan, run=session.exec)


async def _async_null_fks_for_nested_deletes(session: AsyncSession, plan: WritePlan) -> None:
    fk_nulling = nested_delete_fk_nulling(plan)
    if not fk_nulling or plan.root.where is None:
        return
    table = plan.root.table
    stmt = update(table).values(**fk_nulling)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)


def _assert_replace_nested_exclusive(
    session: Any,
    plan: WritePlan,
    field_name: str,
    delete_plan: DeletePlan,
) -> None:
    assert_replace_nested_exclusive(
        plan,
        field_name,
        delete_plan,
        run_count=lambda stmt: session.exec(stmt).one(),
    )


async def _async_assert_replace_nested_exclusive(
    session: AsyncSession,
    plan: WritePlan,
    field_name: str,
    delete_plan: DeletePlan,
) -> None:
    from ontosql.compile._sql_runner import (
        check_replace_nested_exclusive,
        replace_nested_exclusive_count_stmt,
    )

    stmt = replace_nested_exclusive_count_stmt(plan, field_name, delete_plan)
    if stmt is None:
        return
    nested_id = nested_delete_identity(delete_plan)
    result = await session.execute(stmt)
    count = count_scalar(result.one())
    check_replace_nested_exclusive(count, field_name, nested_id)


def _execute_collection_writes(
    session: Any,
    plan: WritePlan,
    parent_id: Any,
) -> None:
    if parent_id is None:
        return
    for cwp in plan.collections:
        cmap = plan.mapper_cls.collection_maps[cwp.field_name]
        through_table = cmap.through_table
        source_key = _column_key(cmap.source_fk)
        target_key = _column_key(cmap.target_fk)
        stmt = delete(through_table).where(through_table.c[source_key] == parent_id)
        session.exec(stmt)

        target_ids: list[Any] = []
        policy = CascadePolicy(cwp.policy)
        if policy is CascadePolicy.LINK:
            for item in cwp.items:
                tid = getattr(item, cmap.nested_mapper.identity_field, None)
                if tid is None:
                    raise ExecuteError(
                        f"Collection {cwp.field_name!r} link requires nested identity"
                    )
                target_ids.append(tid)
        else:
            for idx, nested_plan in enumerate(cwp.nested_writes):
                tid = execute_write_plan(session, nested_plan)
                if tid is None:
                    tid = getattr(
                        cwp.items[idx],
                        nested_plan.mapper_cls.identity_field,
                        None,
                    )
                target_ids.append(tid)

        for tid in target_ids:
            session.exec(insert(through_table).values({source_key: parent_id, target_key: tid}))


async def _async_execute_collection_writes(
    session: AsyncSession,
    plan: WritePlan,
    parent_id: Any,
) -> None:
    if parent_id is None:
        return
    for cwp in plan.collections:
        cmap = plan.mapper_cls.collection_maps[cwp.field_name]
        through_table = cmap.through_table
        source_key = _column_key(cmap.source_fk)
        target_key = _column_key(cmap.target_fk)
        stmt = delete(through_table).where(through_table.c[source_key] == parent_id)
        await session.execute(stmt)

        target_ids: list[Any] = []
        policy = CascadePolicy(cwp.policy)
        if policy is CascadePolicy.LINK:
            for item in cwp.items:
                tid = getattr(item, cmap.nested_mapper.identity_field, None)
                if tid is None:
                    raise ExecuteError(
                        f"Collection {cwp.field_name!r} link requires nested identity"
                    )
                target_ids.append(tid)
        else:
            for idx, nested_plan in enumerate(cwp.nested_writes):
                tid = await async_execute_write_plan(session, nested_plan)
                if tid is None:
                    tid = getattr(
                        cwp.items[idx],
                        nested_plan.mapper_cls.identity_field,
                        None,
                    )
                target_ids.append(tid)

        for tid in target_ids:
            await session.execute(
                insert(through_table).values({source_key: parent_id, target_key: tid})
            )


def execute_write_plan(session: Any, plan: WritePlan) -> Any:
    """Execute a WritePlan synchronously; returns root identity value after insert."""
    _null_fks_for_nested_deletes(session, plan)
    for field_name, delete_plan in plan.nested_deletes:
        _assert_replace_nested_exclusive(session, plan, field_name, delete_plan)
        execute_delete_plan(session, delete_plan)

    fk_updates = dict(plan.fk_updates)
    for field_name, nested in plan.nested:
        nested_id = execute_write_plan(session, nested)
        _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

    table = plan.root.table
    values = dict(plan.root.values)
    values.update(fk_updates)

    if plan.operation == "insert":
        result = session.exec(insert(table).values(**values))
        parent_id = _inserted_identity(result, plan, values)
        _execute_collection_writes(session, plan, parent_id)
        return parent_id

    if values:
        stmt = update(table).values(**values)
        if plan.root.where is not None:
            stmt = _apply_where(stmt, table, plan.root.where)
        session.exec(stmt)

    parent_id = _update_identity(plan)
    _execute_collection_writes(session, plan, parent_id)
    return parent_id


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
    await _async_null_fks_for_nested_deletes(session, plan)
    for field_name, delete_plan in plan.nested_deletes:
        await _async_assert_replace_nested_exclusive(session, plan, field_name, delete_plan)
        await async_execute_delete_plan(session, delete_plan)

    fk_updates = dict(plan.fk_updates)
    for field_name, nested in plan.nested:
        nested_id = await async_execute_write_plan(session, nested)
        _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

    table = plan.root.table
    values = dict(plan.root.values)
    values.update(fk_updates)

    if plan.operation == "insert":
        result = await session.execute(insert(table).values(**values))
        parent_id = _inserted_identity(result, plan, values)
        await _async_execute_collection_writes(session, plan, parent_id)
        return parent_id

    if values:
        stmt = update(table).values(**values)
        if plan.root.where is not None:
            stmt = _apply_where(stmt, table, plan.root.where)
        await session.execute(stmt)

    parent_id = _update_identity(plan)
    await _async_execute_collection_writes(session, plan, parent_id)
    return parent_id


async def async_execute_delete_plan(session: AsyncSession, plan: DeletePlan) -> None:
    """Execute a DeletePlan on an AsyncSession."""
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)
