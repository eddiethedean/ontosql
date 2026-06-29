"""Shared SQL helpers for sync and async OntoSession."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ontosql.compile.plan import WritePlan
from ontosql.compile.select import compile_select_plan
from ontosql.semantic.model import OntoModel
from ontosql.session._ops import reload_identity
from ontosql.session.collections import attach_collections, attach_collections_async
from ontosql.session.hydrate import hydrate_first


def snapshot_from_select_result(
    plan: Any,
    result: Any,
    *,
    mapper_cls: type[Any] | None = None,
    session: Any | None = None,
) -> dict[str, Any] | None:
    """Hydrate a select plan result into a snapshot dict."""
    row_instance = hydrate_first(plan, result)
    if row_instance is None:
        return None
    if session is not None and mapper_cls is not None and mapper_cls.collection_maps:
        attach_collections(session, mapper_cls, [row_instance])
    return row_instance.model_dump()


def load_snapshot_from_db(
    instance: OntoModel,
    mapper_cls: type[Any],
    *,
    run_select: Callable[[Any], Any],
    session: Any | None = None,
) -> dict[str, Any] | None:
    identity = getattr(instance, mapper_cls.identity_field, None)
    if identity is None:
        return None
    plan = compile_select_plan(mapper_cls, id_value=identity, limit=1)
    return snapshot_from_select_result(
        plan,
        run_select(plan.select),
        mapper_cls=mapper_cls,
        session=session,
    )


async def async_snapshot_from_select_result(
    plan: Any,
    result: Any,
    *,
    mapper_cls: type[Any] | None = None,
    session: Any | None = None,
) -> dict[str, Any] | None:
    row_instance = hydrate_first(plan, result)
    if row_instance is None:
        return None
    if session is not None and mapper_cls is not None and mapper_cls.collection_maps:
        await attach_collections_async(session, mapper_cls, [row_instance])
    return row_instance.model_dump()


async def async_load_snapshot_from_db(
    instance: OntoModel,
    mapper_cls: type[Any],
    *,
    run_select: Callable[[Any], Awaitable[Any]],
    session: Any | None = None,
) -> dict[str, Any] | None:
    identity = getattr(instance, mapper_cls.identity_field, None)
    if identity is None:
        return None
    plan = compile_select_plan(mapper_cls, id_value=identity, limit=1)
    result = await run_select(plan.select)
    return await async_snapshot_from_select_result(
        plan,
        result,
        mapper_cls=mapper_cls,
        session=session,
    )


def reload_after_save(
    instance: OntoModel,
    mapper_cls: type[Any],
    plan: WritePlan,
    inserted_id: Any,
    *,
    get_fn: Callable[..., OntoModel | None],
) -> OntoModel:
    identity = reload_identity(instance, mapper_cls, plan, inserted_id)
    if identity is not None:
        reloaded = get_fn(type(instance), identity=identity)
        if reloaded is not None:
            return reloaded
    return instance


async def async_reload_after_save(
    instance: OntoModel,
    mapper_cls: type[Any],
    plan: WritePlan,
    inserted_id: Any,
    *,
    get_fn: Callable[..., Awaitable[OntoModel | None]],
) -> OntoModel:
    identity = reload_identity(instance, mapper_cls, plan, inserted_id)
    if identity is not None:
        reloaded = await get_fn(type(instance), identity=identity)
        if reloaded is not None:
            return reloaded
    return instance
