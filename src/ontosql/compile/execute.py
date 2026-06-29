"""Execute compiled write and delete plans against SQLAlchemy."""

from __future__ import annotations

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
    nested_delete_identity,
)
from ontosql.compile.columns import column_key, count_scalar
from ontosql.compile.execute_runner import (
    apply_nested_fk_updates,
    assert_delete_exclusive,
    async_null_fks,
    inserted_identity,
    make_assert_member_delete,
    run_collection_writes,
    run_delete_plan,
    run_write_plan,
    sync_null_fks,
    update_identity,
    update_rowcount,
)
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.mapping.cascade import CascadePolicy

# Backward-compatible private aliases for tests
_inserted_identity = inserted_identity
_update_identity = update_identity
_apply_nested_fk_updates = apply_nested_fk_updates
_update_rowcount = update_rowcount

__all__ = [
    "ExecuteError",
    "assert_delete_exclusive",
    "async_execute_delete_plan",
    "async_execute_write_plan",
    "execute_delete_plan",
    "execute_write_plan",
]


@dataclass
class _SyncWriteExecutor:
    session: Any
    mapper_registry: Any | None = None
    strict_updates: bool = True

    def execute_write(self, plan: WritePlan) -> Any:
        return run_write_plan(
            plan,
            null_fks=lambda p: sync_null_fks(self.session, p),
            assert_replace=self._assert_replace,
            run_stmt=self.session.exec,
            execute_write=self.execute_write,
            execute_delete=lambda p: execute_delete_plan(
                self.session, p, mapper_registry=self.mapper_registry
            ),
            run_collection=self._run_collection_writes,
            strict_updates=self.strict_updates,
        )

    def _assert_replace(self, plan: WritePlan, field_name: str, delete_plan: DeletePlan) -> None:
        assert_replace_nested_exclusive(
            plan,
            field_name,
            delete_plan,
            run_count=lambda stmt: self.session.exec(stmt).one(),
            mapper_registry=self.mapper_registry,
        )

    def _run_collection_writes(self, plan: WritePlan, parent_id: Any) -> None:
        def run_count(stmt: Any) -> Any:
            return self.session.exec(stmt).one()

        run_collection_writes(
            plan,
            parent_id,
            run_stmt=self.session.exec,
            execute_write=self.execute_write,
            execute_delete=lambda p: execute_delete_plan(
                self.session, p, mapper_registry=self.mapper_registry
            ),
            assert_member_delete=make_assert_member_delete(run_count, self.mapper_registry),
        )


@dataclass
class _AsyncWriteExecutor:
    session: AsyncSession
    mapper_registry: Any | None = None
    strict_updates: bool = True

    async def execute_write(self, plan: WritePlan) -> Any:
        await async_null_fks(self.session, plan)

        table = plan.root.table
        values = dict(plan.root.values)
        fk_updates = dict(plan.fk_updates)

        if plan.operation == "insert":
            for field_name, delete_plan in plan.nested_deletes:
                await self._assert_replace(plan, field_name, delete_plan)
                await async_execute_delete_plan(
                    self.session, delete_plan, mapper_registry=self.mapper_registry
                )
            for field_name, nested in plan.nested:
                nested_id = await self.execute_write(nested)
                from ontosql.compile.execute_runner import apply_nested_fk_updates

                apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)
            values.update(fk_updates)
            result = await self.session.execute(insert(table).values(**values))
            parent_id = inserted_identity(result, plan, values)
            await self._run_collection_writes(plan, parent_id)
            return parent_id

        parent_id = update_identity(plan)
        if plan.collections:
            await self._run_collection_writes(plan, parent_id)

        for field_name, delete_plan in plan.nested_deletes:
            await self._assert_replace(plan, field_name, delete_plan)
            await async_execute_delete_plan(
                self.session, delete_plan, mapper_registry=self.mapper_registry
            )

        for field_name, nested in plan.nested:
            nested_id = await self.execute_write(nested)
            from ontosql.compile.execute_runner import apply_nested_fk_updates

            apply_nested_fk_updates(plan, fk_updates, field_name, nested_id)

        values.update(fk_updates)

        if values:
            stmt = update(table).values(**values)
            if plan.root.where is not None:
                stmt = _apply_where(stmt, table, plan.root.where)
            result = await self.session.execute(stmt)
            if self.strict_updates and update_rowcount(result) == 0:
                raise ExecuteError("Update affected 0 rows")

        return parent_id

    async def _assert_replace(
        self, plan: WritePlan, field_name: str, delete_plan: DeletePlan
    ) -> None:
        if self.mapper_registry is None:
            raise ExecuteError(
                "REPLACE nested delete requires mapper_registry= for cross-table FK safety"
            )
        nested_id = nested_delete_identity(delete_plan)
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
            source_key = column_key(cmap.source_fk)
            target_key = column_key(cmap.target_fk)
            await self.session.execute(
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
                await self.session.execute(
                    insert(through_table).values({source_key: parent_id, target_key: tid})
                )
            for member_delete in cwp.member_deletes:
                nested_id = nested_delete_identity(member_delete)
                if self.mapper_registry is None:
                    raise ExecuteError("Collection REPLACE member delete requires mapper_registry=")
                stmts = inbound_fk_count_stmts(self.mapper_registry, member_delete)
                total = 0
                for _, stmt in stmts:
                    result = await self.session.execute(stmt)
                    total += count_scalar(result.one())
                check_replace_nested_exclusive(total, cwp.field_name, nested_id)
                await async_execute_delete_plan(
                    self.session, member_delete, mapper_registry=self.mapper_registry
                )


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
    ).execute_write(plan)


def execute_delete_plan(
    session: Any,
    plan: DeletePlan,
    *,
    mapper_registry: Any | None = None,
) -> None:
    """Execute a DeletePlan synchronously."""

    def execute_nested(nested: DeletePlan) -> None:
        execute_delete_plan(session, nested, mapper_registry=mapper_registry)

    run_delete_plan(
        plan,
        mapper_registry=mapper_registry,
        run_count=lambda stmt: session.exec(stmt).one(),
        execute_nested=execute_nested,
        run_stmt=session.exec,
    )


async def async_execute_delete_plan(
    session: AsyncSession,
    plan: DeletePlan,
    *,
    mapper_registry: Any | None = None,
) -> None:
    """Execute a DeletePlan on an AsyncSession."""

    async def execute_nested(nested: DeletePlan) -> None:
        await async_execute_delete_plan(session, nested, mapper_registry=mapper_registry)

    for field_name, nested_plan in plan.nested_deletes:
        nested_id = nested_delete_identity(nested_plan)
        if mapper_registry is None:
            raise ExecuteError(
                "DELETE nested cascade requires mapper_registry= for cross-table FK safety"
            )
        stmts = inbound_fk_count_stmts(
            mapper_registry,
            nested_plan,
            exclude_table=plan.root.table,
            exclude_where=plan.root.where,
        )
        total = 0
        for _, stmt in stmts:
            result = await session.execute(stmt)
            total += count_scalar(result.one())
        check_replace_nested_exclusive(total, field_name, nested_id)
        await execute_nested(nested_plan)
    if plan.root.where is None:
        raise ExecuteError("delete plan requires where clause")
    table = plan.root.table
    stmt = delete(table)
    stmt = _apply_where(stmt, table, plan.root.where)
    await session.execute(stmt)


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
    ).execute_write(plan)
