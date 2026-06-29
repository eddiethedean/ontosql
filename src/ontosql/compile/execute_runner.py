"""Shared sync/async write and delete plan execution algorithms."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy import delete, insert, update

from ontosql.compile._sql_runner import (
    ExecuteError,
    _apply_where,
    assert_replace_nested_exclusive,
    check_replace_nested_exclusive,
    inbound_fk_count_stmts,
    nested_delete_fk_nulling,
    nested_delete_identity,
    run_null_fks_for_nested_deletes,
)
from ontosql.compile.columns import column_key, count_scalar
from ontosql.compile.plan import CollectionWritePlan, DeletePlan, WritePlan
from ontosql.mapping.cascade import CascadePolicy

T = TypeVar("T")


def inserted_identity(result: Any, plan: WritePlan, values: dict[str, Any]) -> Any:
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


def apply_nested_fk_updates(
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
    fk_updates[column_key(nmap.fk_column)] = nested_id


def update_identity(plan: WritePlan) -> Any:
    if plan.root.where is None:
        return None
    identity_col = plan.mapper_cls.identity_field
    identity_key = identity_col
    if identity_col in plan.mapper_cls.column_maps:
        col = plan.mapper_cls.column_maps[identity_col].column
        identity_key = getattr(col, "key", None) or getattr(col, "name", identity_col)
    return plan.root.where.get(str(identity_key))


def update_rowcount(result: Any) -> int:
    rowcount = getattr(result, "rowcount", None)
    if rowcount is None:
        return 0
    return int(rowcount)


def collection_target_ids(
    plan: WritePlan,
    cwp: CollectionWritePlan,
    *,
    execute_nested: Callable[[WritePlan], Any],
) -> list[Any]:
    cmap = plan.mapper_cls.collection_maps[cwp.field_name]
    target_ids: list[Any] = []
    if cwp.policy is CascadePolicy.LINK:
        for item in cwp.items:
            tid = getattr(item, cmap.nested_mapper.identity_field, None)
            if tid is None:
                raise ExecuteError(f"Collection {cwp.field_name!r} link requires nested identity")
            target_ids.append(tid)
    else:
        for idx, nested_plan in enumerate(cwp.nested_writes):
            tid = execute_nested(nested_plan)
            if tid is None:
                tid = getattr(
                    cwp.items[idx],
                    nested_plan.mapper_cls.identity_field,
                    None,
                )
            target_ids.append(tid)
    return target_ids


def run_collection_writes(
    plan: WritePlan,
    parent_id: Any,
    *,
    run_stmt: Callable[[Any], Any],
    execute_write: Callable[[WritePlan], Any],
    execute_delete: Callable[[DeletePlan], None],
    assert_member_delete: Callable[[DeletePlan, str], None],
) -> None:
    if plan.collections and parent_id is None:
        raise ExecuteError(
            "Cannot write collection fields: parent identity could not be resolved after insert"
        )
    if parent_id is None:
        return
    for cwp in plan.collections:
        cmap = plan.mapper_cls.collection_maps[cwp.field_name]
        through_table = cmap.through_table
        source_key = column_key(cmap.source_fk)
        target_key = column_key(cmap.target_fk)
        run_stmt(delete(through_table).where(through_table.c[source_key] == parent_id))
        target_ids = collection_target_ids(plan, cwp, execute_nested=execute_write)
        for tid in target_ids:
            run_stmt(insert(through_table).values({source_key: parent_id, target_key: tid}))
        for member_delete in cwp.member_deletes:
            assert_member_delete(member_delete, cwp.field_name)
            execute_delete(member_delete)


def run_write_plan(
    plan: WritePlan,
    *,
    null_fks: Callable[[WritePlan], Any],
    assert_replace: Callable[[WritePlan, str, DeletePlan], Any],
    run_stmt: Callable[[Any], Any],
    execute_write: Callable[[WritePlan], Any],
    execute_delete: Callable[[DeletePlan], None],
    run_collection: Callable[[WritePlan, Any], Any],
    strict_updates: bool = True,
) -> Any:
    null_fks(plan)

    table = plan.root.table
    values = dict(plan.root.values)
    fk_updates = dict(plan.fk_updates)

    if plan.operation == "insert":
        for field_name, delete_plan in plan.nested_deletes:
            assert_replace(plan, field_name, delete_plan)
            execute_delete(delete_plan)
        for field_name, nested in plan.nested:
            nested_id = execute_write(nested)
            apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)
        values.update(fk_updates)
        result = run_stmt(insert(table).values(**values))
        parent_id = inserted_identity(result, plan, values)
        run_collection(plan, parent_id)
        return parent_id

    parent_id = update_identity(plan)
    if plan.collections:
        run_collection(plan, parent_id)

    for field_name, delete_plan in plan.nested_deletes:
        assert_replace(plan, field_name, delete_plan)
        execute_delete(delete_plan)

    for field_name, nested in plan.nested:
        nested_id = execute_write(nested)
        apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

    values.update(fk_updates)

    if values:
        stmt = update(table).values(**values)
        if plan.root.where is not None:
            stmt = _apply_where(stmt, table, plan.root.where)
        result = run_stmt(stmt)
        if strict_updates and update_rowcount(result) == 0:
            raise ExecuteError("Update affected 0 rows")

    return parent_id


def assert_delete_exclusive(
    delete_plan: DeletePlan,
    *,
    field_name: str,
    run_count: Callable[[Any], Any],
    mapper_registry: Any | None,
    exclude_table: Any | None = None,
    exclude_where: dict[str, Any] | None = None,
) -> None:
    nested_id = nested_delete_identity(delete_plan)
    if mapper_registry is None:
        raise ExecuteError(
            "DELETE nested cascade requires mapper_registry= for cross-table FK safety"
        )
    stmts = inbound_fk_count_stmts(
        mapper_registry,
        delete_plan,
        exclude_table=exclude_table,
        exclude_where=exclude_where,
    )
    total = sum(count_scalar(run_count(stmt)) for _, stmt in stmts)
    check_replace_nested_exclusive(total, field_name, nested_id)


def run_delete_plan(
    plan: DeletePlan,
    *,
    mapper_registry: Any | None,
    run_count: Callable[[Any], Any],
    execute_nested: Callable[[DeletePlan], Any],
    run_stmt: Callable[[Any], Any],
) -> None:
    for field_name, nested_plan in plan.nested_deletes:
        assert_delete_exclusive(
            nested_plan,
            field_name=field_name,
            run_count=run_count,
            mapper_registry=mapper_registry,
            exclude_table=plan.root.table,
            exclude_where=plan.root.where,
        )
        execute_nested(nested_plan)
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    run_stmt(stmt)


def sync_null_fks(session: Any, plan: WritePlan) -> None:
    run_null_fks_for_nested_deletes(plan, run=session.exec)


async def async_null_fks(session: Any, plan: WritePlan) -> None:
    fk_nulling = nested_delete_fk_nulling(plan)
    if not fk_nulling or plan.root.where is None:
        return
    table = plan.root.table
    stmt = update(table).values(**fk_nulling)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)


def make_assert_replace_sync(session: Any, mapper_registry: Any | None):
    def _assert_replace(plan: WritePlan, field_name: str, delete_plan: DeletePlan) -> None:
        assert_replace_nested_exclusive(
            plan,
            field_name,
            delete_plan,
            run_count=lambda stmt: session.exec(stmt).one(),
            mapper_registry=mapper_registry,
        )

    return _assert_replace


def make_assert_replace_async(session: Any, mapper_registry: Any | None):
    async def _assert_replace(plan: WritePlan, field_name: str, delete_plan: DeletePlan) -> None:
        assert_replace_nested_exclusive(
            plan,
            field_name,
            delete_plan,
            run_count=lambda stmt: session.execute(stmt).one(),
            mapper_registry=mapper_registry,
        )

    return _assert_replace


def make_assert_member_delete(run_count: Callable[[Any], Any], mapper_registry: Any | None):
    def _assert(member_delete: DeletePlan, field_name: str) -> None:
        assert_delete_exclusive(
            member_delete,
            field_name=field_name,
            run_count=run_count,
            mapper_registry=mapper_registry,
        )

    return _assert
