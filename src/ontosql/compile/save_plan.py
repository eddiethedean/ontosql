"""Compile semantic instances to INSERT/UPDATE/DELETE plans."""

from __future__ import annotations

from typing import Any

from ontosql.compile.collection_write import compile_collections
from ontosql.compile.columns import column_key
from ontosql.compile.errors import WriteCompileError
from ontosql.compile.nested_write import (
    compile_nested,
    delete_plan_for_identity,
    snapshot_nested_identity,
)
from ontosql.compile.plan import DeletePlan, TableWrite, WritePlan
from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import ColumnMap
from ontosql.semantic.model import OntoModel


def _identity_unset(mapper_cls: type[Any], instance: OntoModel) -> bool:
    identity = mapper_cls.identity_field
    if identity not in mapper_cls.column_maps:
        raise WriteCompileError(f"Mapper {mapper_cls.__name__} has no identity column map")
    value = getattr(instance, identity, None)
    return value is None


def _root_values(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    partial_fields: set[str] | None,
    include_identity: bool,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_name, cmap in mapper_cls.column_maps.items():
        if field_name in mapper_cls.nested_maps:
            continue
        if partial_fields is not None and field_name not in partial_fields:
            continue
        if field_name == mapper_cls.identity_field and not include_identity:
            continue
        col_key = column_key(cmap.column)
        value = getattr(instance, field_name)
        if field_name == mapper_cls.identity_field and value is None:
            continue
        values[col_key] = value
    return values


def compile_save_plan(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    partial_fields: set[str] | None = None,
    is_new: bool | None = None,
    snapshot: dict[str, Any] | None = None,
) -> WritePlan:
    """Build a WritePlan for save()."""
    new = _identity_unset(mapper_cls, instance) if is_new is None else is_new
    operation: str = "insert" if new else "update"

    if partial_fields is not None:
        computed_in_partial = partial_fields & set(mapper_cls.computed_maps)
        if computed_in_partial:
            raise WriteCompileError(
                f"Cannot persist computed fields: {sorted(computed_in_partial)!r}"
            )

    if new:
        partial = None
        include_identity = True
    else:
        partial = partial_fields
        include_identity = False

    root_table = mapper_cls.primary_table
    if root_table is None:
        raise WriteCompileError(f"Mapper {mapper_cls.__name__} has no primary_table")

    values = _root_values(
        mapper_cls,
        instance,
        partial_fields=partial,
        include_identity=include_identity,
    )

    where: dict[str, Any] | None = None
    if not new:
        identity = mapper_cls.identity_field
        identity_col = mapper_cls.column_maps[identity]
        where = {column_key(identity_col.column): getattr(instance, identity)}

    if not new and snapshot is None:
        for field_name, nmap in mapper_cls.nested_maps.items():
            if nmap.cascade is not CascadePolicy.REPLACE:
                continue
            if partial_fields is None or field_name in partial_fields:
                raise WriteCompileError(
                    f"REPLACE cascade on {field_name!r} requires snapshot= on update"
                )

    nested_plans, nested_deletes, fk_updates = compile_nested(
        mapper_cls,
        instance,
        partial_fields=partial_fields if not new else None,
        snapshot=snapshot,
        is_new=new,
    )

    collection_plans = compile_collections(
        mapper_cls,
        instance,
        partial_fields=partial_fields if not new else None,
        snapshot=snapshot,
    )

    return WritePlan(
        mapper_cls=mapper_cls,
        operation=operation,  # type: ignore[arg-type]
        root=TableWrite(table=root_table, values=values, where=where),
        nested=nested_plans,
        nested_deletes=nested_deletes,
        fk_updates=fk_updates,
        collections=collection_plans,
    )


def compile_delete_plan(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    snapshot: dict[str, Any] | None = None,
) -> DeletePlan:
    """Build a DeletePlan for delete() — root row plus REPLACE nested cascades."""
    identity = mapper_cls.identity_field
    if identity not in mapper_cls.column_maps:
        raise WriteCompileError(f"Mapper {mapper_cls.__name__} has no identity column map")
    identity_value = getattr(instance, identity, None)
    if identity_value is None:
        raise WriteCompileError("delete() requires instance identity")

    identity_col: ColumnMap = mapper_cls.column_maps[identity]
    root_table = mapper_cls.primary_table
    if root_table is None:
        raise WriteCompileError(f"Mapper {mapper_cls.__name__} has no primary_table")

    nested_deletes: list[tuple[str, DeletePlan]] = []
    for field_name, nmap in mapper_cls.nested_maps.items():
        if nmap.cascade is not CascadePolicy.REPLACE:
            continue
        nested_value = getattr(instance, field_name, None)
        nested_id: Any | None = None
        if nested_value is not None:
            from ontosql.compile.nested_write import identity_value as nested_identity

            nested_id = nested_identity(nmap.nested_mapper, nested_value)
        if nested_id is None:
            nested_id = snapshot_nested_identity(snapshot, field_name, nmap.nested_mapper)
        if nested_id is not None:
            nested_deletes.append(
                (field_name, delete_plan_for_identity(nmap.nested_mapper, nested_id))
            )

    return DeletePlan(
        mapper_cls=mapper_cls,
        root=TableWrite(
            table=root_table,
            where={column_key(identity_col.column): identity_value},
        ),
        nested_deletes=nested_deletes,
    )
