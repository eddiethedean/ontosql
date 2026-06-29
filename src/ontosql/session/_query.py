"""Shared find/count helpers for sync and async sessions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ontosql.compile.select import compile_select_plan
from ontosql.semantic.model import OntoModel
from ontosql.session.hydrate import hydrate_row
from ontosql.session.state import SessionState


def count_pending_deletes_matching(
    state: SessionState,
    mapper_cls: type[Any],
    entity_type: type[OntoModel],
    *,
    where: Any | None,
    run_select_first: Callable[[Any], Any],
) -> int:
    """Count tombstoned deletes that would match ``where`` (for adjusted count())."""
    matches = 0
    for et, identity in state.pending_deletes:
        if et is not entity_type:
            continue
        plan = compile_select_plan(mapper_cls, id_value=identity, where=where, limit=1)
        if run_select_first(plan.select) is not None:
            matches += 1
    return matches


async def count_pending_deletes_matching_async(
    state: SessionState,
    mapper_cls: type[Any],
    entity_type: type[OntoModel],
    *,
    where: Any | None,
    run_select_first: Callable[[Any], Awaitable[Any]],
) -> int:
    matches = 0
    for et, identity in state.pending_deletes:
        if et is not entity_type:
            continue
        plan = compile_select_plan(mapper_cls, id_value=identity, where=where, limit=1)
        if await run_select_first(plan.select) is not None:
            matches += 1
    return matches


def find_with_limit(
    state: SessionState,
    mapper_cls: type[Any],
    entity_type: type[OntoModel],
    *,
    where: Any | None,
    order_by: Any | None,
    limit: int,
    offset: int | None,
    run_select_all: Callable[[Any], list[Any]],
    attach: Callable[[list[OntoModel]], None],
    register: Callable[[OntoModel], OntoModel],
) -> list[OntoModel]:
    """find() with limit, over-fetching past pending-delete tombstones."""
    result: list[OntoModel] = []
    sql_offset = offset or 0
    chunk = limit
    while len(result) < limit:
        plan = compile_select_plan(
            mapper_cls,
            where=where,
            order_by=order_by,
            limit=chunk,
            offset=sql_offset,
        )
        rows = run_select_all(plan.select)
        if not rows:
            break
        instances = [hydrate_row(plan, row) for row in rows]
        attach(instances)
        for inst in instances:
            identity = getattr(inst, mapper_cls.identity_field, None)
            if identity is not None and state.is_pending_delete(entity_type, identity):
                continue
            result.append(register(inst))
            if len(result) >= limit:
                break
        sql_offset += len(rows)
        if len(rows) < chunk:
            break
    return result


async def find_with_limit_async(
    state: SessionState,
    mapper_cls: type[Any],
    entity_type: type[OntoModel],
    *,
    where: Any | None,
    order_by: Any | None,
    limit: int,
    offset: int | None,
    run_select_all: Callable[[Any], Awaitable[list[Any]]],
    attach: Callable[[list[OntoModel]], Awaitable[None]],
    register: Callable[[OntoModel], OntoModel],
) -> list[OntoModel]:
    """Async find() with limit, over-fetching past pending-delete tombstones."""
    result: list[OntoModel] = []
    sql_offset = offset or 0
    chunk = limit
    while len(result) < limit:
        plan = compile_select_plan(
            mapper_cls,
            where=where,
            order_by=order_by,
            limit=chunk,
            offset=sql_offset,
        )
        rows = await run_select_all(plan.select)
        if not rows:
            break
        instances = [hydrate_row(plan, row) for row in rows]
        await attach(instances)
        for inst in instances:
            identity = getattr(inst, mapper_cls.identity_field, None)
            if identity is not None and state.is_pending_delete(entity_type, identity):
                continue
            result.append(register(inst))
            if len(result) >= limit:
                break
        sql_offset += len(rows)
        if len(rows) < chunk:
            break
    return result
