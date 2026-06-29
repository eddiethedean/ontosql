"""Shared session operation helpers (sync/async agnostic)."""

from __future__ import annotations

from typing import Any

from ontosql.compile.plan import WritePlan
from ontosql.compile.write import compile_save_plan
from ontosql.semantic.model import OntoModel
from ontosql.session.state import SessionState


def validate_get_identity(
    *,
    identity: Any | None = None,
    iri: str | None = None,
) -> Any | None:
    """Validate get() arguments; returns identity or None when loading by iri=."""
    if identity is None and iri is None:
        raise ValueError("get() requires identity= or iri=")
    if identity is not None and iri is not None:
        raise ValueError("get() accepts only one of identity= or iri=")
    return identity


def resolve_save_is_new_and_snapshot(
    state: SessionState,
    instance: OntoModel,
    *,
    is_new: bool,
    db_snapshot: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any] | None]:
    """Resolve insert vs update and the snapshot used for compile_save_plan."""
    session_snapshot = state.get_snapshot(instance)
    if is_new:
        if db_snapshot is not None:
            return False, db_snapshot
        return True, session_snapshot
    if session_snapshot is not None:
        return False, session_snapshot
    return False, db_snapshot


def compile_save_plan_for_instance(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    is_new: bool,
    snapshot: dict[str, Any] | None,
) -> WritePlan:
    return compile_save_plan(
        mapper_cls,
        instance,
        partial_fields=instance.model_fields_set if not is_new else None,
        is_new=is_new,
        snapshot=snapshot,
    )


def identity_from_write_plan(plan: WritePlan, returned: Any) -> Any:
    identity = returned
    if identity is None and plan.root.where:
        identity = next(iter(plan.root.where.values()))
    elif identity is None and plan.mapper_cls.identity_field in plan.root.values:
        identity = plan.root.values[plan.mapper_cls.identity_field]
    return identity


def reload_identity(
    instance: OntoModel,
    mapper_cls: type[Any],
    plan: WritePlan,
    inserted_id: Any,
) -> Any:
    identity = getattr(instance, mapper_cls.identity_field, None)
    if identity is None:
        identity = inserted_id
    if identity is None and plan.root.where:
        identity = next(iter(plan.root.where.values()))
    return identity
