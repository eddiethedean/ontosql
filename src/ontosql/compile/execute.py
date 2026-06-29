"""Execute compiled write and delete plans against SQLAlchemy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from ontosql.compile._sql_runner import (
    ExecuteError,
    _apply_where,
    assert_replace_nested_exclusive,
    check_replace_nested_exclusive,
    inbound_fk_count_stmts,
    nested_delete_fk_nulling,
    run_null_fks_for_nested_deletes,
)
from ontosql.compile.plan import CollectionWritePlan, DeletePlan, WritePlan
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


def _collection_target_ids(
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


def _update_rowcount(result: Any) -> int:
    """Return affected row count from a SQLAlchemy execute result."""
    rowcount = getattr(result, "rowcount", None)
    if rowcount is None:
        return 0
    return int(rowcount)


@dataclass
class _SyncWriteExecutor:
    session: Any
    mapper_registry: Any | None = None
    strict_updates: bool = True

    def null_fks(self, plan: WritePlan) -> None:
        run_null_fks_for_nested_deletes(plan, run=self.session.exec)

    def assert_replace(self, plan: WritePlan, field_name: str, delete_plan: DeletePlan) -> None:
        assert_replace_nested_exclusive(
            plan,
            field_name,
            delete_plan,
            run_count=lambda stmt: self.session.exec(stmt).one(),
            mapper_registry=self.mapper_registry,
        )

    def run_stmt(self, stmt: Any) -> Any:
        return self.session.exec(stmt)

    def execute_write(self, plan: WritePlan) -> Any:
        return self._run_write_plan(plan)

    def execute_delete(self, plan: DeletePlan) -> None:
        execute_delete_plan(self.session, plan)

    def _run_collection_writes(self, plan: WritePlan, parent_id: Any) -> None:
        if plan.collections and parent_id is None:
            raise ExecuteError(
                "Cannot write collection fields: parent identity could not be resolved after insert"
            )
        if parent_id is None:
            return
        for cwp in plan.collections:
            cmap = plan.mapper_cls.collection_maps[cwp.field_name]
            through_table = cmap.through_table
            source_key = _column_key(cmap.source_fk)
            target_key = _column_key(cmap.target_fk)
            self.run_stmt(delete(through_table).where(through_table.c[source_key] == parent_id))
            target_ids = _collection_target_ids(plan, cwp, execute_nested=self.execute_write)
            for tid in target_ids:
                self.run_stmt(
                    insert(through_table).values({source_key: parent_id, target_key: tid})
                )

    def _run_write_plan(self, plan: WritePlan) -> Any:
        self.null_fks(plan)
        for field_name, delete_plan in plan.nested_deletes:
            self.assert_replace(plan, field_name, delete_plan)
            self.execute_delete(delete_plan)

        fk_updates = dict(plan.fk_updates)
        for field_name, nested in plan.nested:
            nested_id = self.execute_write(nested)
            _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

        table = plan.root.table
        values = dict(plan.root.values)
        values.update(fk_updates)

        if plan.operation == "insert":
            result = self.run_stmt(insert(table).values(**values))
            parent_id = _inserted_identity(result, plan, values)
            self._run_collection_writes(plan, parent_id)
            return parent_id

        if values:
            stmt = update(table).values(**values)
            if plan.root.where is not None:
                stmt = _apply_where(stmt, table, plan.root.where)
            result = self.run_stmt(stmt)
            if self.strict_updates and _update_rowcount(result) == 0:
                raise ExecuteError("Update affected 0 rows")

        parent_id = _update_identity(plan)
        self._run_collection_writes(plan, parent_id)
        return parent_id


@dataclass
class _AsyncWriteExecutor:
    session: AsyncSession
    mapper_registry: Any | None = None
    strict_updates: bool = True

    async def null_fks(self, plan: WritePlan) -> None:
        fk_nulling = nested_delete_fk_nulling(plan)
        if not fk_nulling or plan.root.where is None:
            return
        table = plan.root.table
        stmt = update(table).values(**fk_nulling)
        stmt = _apply_where(stmt, table, plan.root.where)
        await self.session.execute(stmt)

    async def assert_replace(
        self, plan: WritePlan, field_name: str, delete_plan: DeletePlan
    ) -> None:
        from ontosql.compile._sql_runner import nested_delete_identity

        nested_id = nested_delete_identity(delete_plan)
        if self.mapper_registry is not None:
            stmts = inbound_fk_count_stmts(
                self.mapper_registry,
                delete_plan,
                exclude_table=plan.root.table,
                exclude_where=plan.root.where,
            )
            total = 0
            for _, stmt in stmts:
                result = await self.session.execute(stmt)
                total += count_scalar(result.one())
            check_replace_nested_exclusive(total, field_name, nested_id)
            return

        from ontosql.compile._sql_runner import replace_nested_exclusive_count_stmt

        stmt = replace_nested_exclusive_count_stmt(plan, field_name, delete_plan)
        if stmt is None:
            return
        result = await self.session.execute(stmt)
        count = count_scalar(result.one())
        check_replace_nested_exclusive(count, field_name, nested_id)

    async def run_stmt(self, stmt: Any) -> Any:
        return await self.session.execute(stmt)

    async def execute_write(self, plan: WritePlan) -> Any:
        return await self._run_write_plan(plan)

    async def execute_delete(self, plan: DeletePlan) -> None:
        await async_execute_delete_plan(self.session, plan)

    async def _run_collection_writes(self, plan: WritePlan, parent_id: Any) -> None:
        if plan.collections and parent_id is None:
            raise ExecuteError(
                "Cannot write collection fields: parent identity could not be resolved after insert"
            )
        if parent_id is None:
            return
        for cwp in plan.collections:
            cmap = plan.mapper_cls.collection_maps[cwp.field_name]
            through_table = cmap.through_table
            source_key = _column_key(cmap.source_fk)
            target_key = _column_key(cmap.target_fk)
            await self.run_stmt(
                delete(through_table).where(through_table.c[source_key] == parent_id)
            )
            target_ids: list[Any] = []
            if cwp.policy is CascadePolicy.LINK:
                for item in cwp.items:
                    tid = getattr(item, cmap.nested_mapper.identity_field, None)
                    if tid is None:
                        raise ExecuteError(
                            f"Collection {cwp.field_name!r} link requires nested identity"
                        )
                    target_ids.append(tid)
            else:
                for idx, nested_plan in enumerate(cwp.nested_writes):
                    tid = await self.execute_write(nested_plan)
                    if tid is None:
                        tid = getattr(
                            cwp.items[idx],
                            nested_plan.mapper_cls.identity_field,
                            None,
                        )
                    target_ids.append(tid)
            for tid in target_ids:
                await self.run_stmt(
                    insert(through_table).values({source_key: parent_id, target_key: tid})
                )

    async def _run_write_plan(self, plan: WritePlan) -> Any:
        await self.null_fks(plan)
        for field_name, delete_plan in plan.nested_deletes:
            await self.assert_replace(plan, field_name, delete_plan)
            await self.execute_delete(delete_plan)

        fk_updates = dict(plan.fk_updates)
        for field_name, nested in plan.nested:
            nested_id = await self.execute_write(nested)
            _apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

        table = plan.root.table
        values = dict(plan.root.values)
        values.update(fk_updates)

        if plan.operation == "insert":
            result = await self.run_stmt(insert(table).values(**values))
            parent_id = _inserted_identity(result, plan, values)
            await self._run_collection_writes(plan, parent_id)
            return parent_id

        if values:
            stmt = update(table).values(**values)
            if plan.root.where is not None:
                stmt = _apply_where(stmt, table, plan.root.where)
            result = await self.run_stmt(stmt)
            if self.strict_updates and _update_rowcount(result) == 0:
                raise ExecuteError("Update affected 0 rows")

        parent_id = _update_identity(plan)
        await self._run_collection_writes(plan, parent_id)
        return parent_id


def execute_write_plan(
    session: Any,
    plan: WritePlan,
    *,
    mapper_registry: Any | None = None,
    strict_updates: bool = True,
) -> Any:
    """Execute a WritePlan synchronously; returns root identity value after insert."""
    return _SyncWriteExecutor(
        session,
        mapper_registry=mapper_registry,
        strict_updates=strict_updates,
    )._run_write_plan(plan)


def execute_delete_plan(session: Any, plan: DeletePlan) -> None:
    """Execute a DeletePlan synchronously."""
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    session.exec(stmt)


async def async_execute_write_plan(
    session: AsyncSession,
    plan: WritePlan,
    *,
    mapper_registry: Any | None = None,
    strict_updates: bool = True,
) -> Any:
    """Execute a WritePlan on an AsyncSession."""
    return await _AsyncWriteExecutor(
        session,
        mapper_registry=mapper_registry,
        strict_updates=strict_updates,
    )._run_write_plan(plan)


async def async_execute_delete_plan(session: AsyncSession, plan: DeletePlan) -> None:
    """Execute a DeletePlan on an AsyncSession."""
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)
