"""Nested field cascade compilation."""

from __future__ import annotations

from typing import Any

from ontosql.compile.columns import column_key
from ontosql.compile.errors import WriteCompileError
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.mapping.cascade import CascadePolicy
from ontosql.semantic.model import OntoModel


def fk_column_key(nmap: Any) -> str:
    if nmap.fk_column is None:
        raise WriteCompileError(
            f"Nested field {nmap.semantic_field!r} requires fk_column for cascade "
            f"{nmap.cascade.value!r}"
        )
    return column_key(nmap.fk_column)


def identity_value(mapper_cls: type[Any], instance: OntoModel) -> Any:
    identity = mapper_cls.identity_field
    return getattr(instance, identity, None)


def snapshot_nested_identity(
    snapshot: dict[str, Any] | None,
    field_name: str,
    nested_mapper: type[Any],
) -> Any:
    if snapshot is None:
        return None
    nested = snapshot.get(field_name)
    if nested is None:
        return None
    identity_field = nested_mapper.identity_field
    if isinstance(nested, dict):
        return nested.get(identity_field)
    return getattr(nested, identity_field, None)


def delete_plan_for_identity(
    nested_mapper: type[Any],
    identity_value: Any,
) -> DeletePlan:
    identity_col = nested_mapper.column_maps[nested_mapper.identity_field]
    root_table = nested_mapper.primary_table
    if root_table is None:
        raise WriteCompileError(f"Mapper {nested_mapper.__name__} has no primary_table")
    return DeletePlan(
        mapper_cls=nested_mapper,
        root=TableWrite(
            table=root_table,
            where={column_key(identity_col.column): identity_value},
        ),
    )


def _handle_nested_none(
    field_name: str,
    nmap: Any,
    policy: CascadePolicy,
    *,
    is_new: bool,
    old_nested_id: Any,
    nested_deletes: list[tuple[str, DeletePlan]],
    fk_updates: dict[str, Any],
) -> bool:
    """Return True when processing should continue to next field."""
    if policy is CascadePolicy.LINK or policy is CascadePolicy.UPSERT and not is_new:
        fk_updates[fk_column_key(nmap)] = None
    elif policy is CascadePolicy.REPLACE and not is_new and old_nested_id is not None:
        nested_deletes.append(
            (field_name, delete_plan_for_identity(nmap.nested_mapper, old_nested_id))
        )
        fk_updates[fk_column_key(nmap)] = None
    return True


def compile_nested(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    partial_fields: set[str] | None,
    snapshot: dict[str, Any] | None = None,
    is_new: bool = False,
) -> tuple[list[tuple[str, WritePlan]], list[tuple[str, DeletePlan]], dict[str, Any]]:
    nested_plans: list[tuple[str, WritePlan]] = []
    nested_deletes: list[tuple[str, DeletePlan]] = []
    fk_updates: dict[str, Any] = {}

    for field_name, nmap in mapper_cls.nested_maps.items():
        if partial_fields is not None and field_name not in partial_fields:
            continue
        nested_value = getattr(instance, field_name, None)
        policy = nmap.cascade
        old_nested_id = snapshot_nested_identity(snapshot, field_name, nmap.nested_mapper)

        if policy is CascadePolicy.IGNORE:
            continue

        if nested_value is None:
            _handle_nested_none(
                field_name,
                nmap,
                policy,
                is_new=is_new,
                old_nested_id=old_nested_id,
                nested_deletes=nested_deletes,
                fk_updates=fk_updates,
            )
            continue

        if policy is CascadePolicy.LINK:
            nested_id = identity_value(nmap.nested_mapper, nested_value)
            if nested_id is None:
                raise WriteCompileError(
                    f"Nested {field_name!r} requires an identity for cascade=link"
                )
            fk_updates[fk_column_key(nmap)] = nested_id
            continue

        new_nested_id = identity_value(nmap.nested_mapper, nested_value)
        if (
            policy is CascadePolicy.REPLACE
            and not is_new
            and old_nested_id is not None
            and old_nested_id != new_nested_id
        ):
            nested_deletes.append(
                (field_name, delete_plan_for_identity(nmap.nested_mapper, old_nested_id))
            )

        nested_partial = None
        nested_snapshot = None
        if snapshot is not None:
            nested_raw = snapshot.get(field_name)
            if isinstance(nested_raw, dict):
                nested_snapshot = nested_raw
        if partial_fields is not None and field_name in partial_fields:
            nested_partial = set(nested_value.model_fields_set)
        from ontosql.compile.save_plan import compile_save_plan

        nested_plan = compile_save_plan(
            nmap.nested_mapper,
            nested_value,
            partial_fields=nested_partial,
            snapshot=nested_snapshot,
        )
        nested_plans.append((field_name, nested_plan))
        if new_nested_id is not None:
            fk_updates[fk_column_key(nmap)] = new_nested_id

    return nested_plans, nested_deletes, fk_updates
