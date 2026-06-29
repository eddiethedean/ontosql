"""Compile semantic instances to INSERT/UPDATE/DELETE plans."""

from __future__ import annotations

from typing import Any

from ontosql.compile.plan import CollectionWritePlan, DeletePlan, TableWrite, WritePlan
from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import ColumnMap
from ontosql.semantic.model import OntoModel


class WriteCompileError(Exception):
    """Raised when a semantic instance cannot be compiled for write."""


def count_scalar(row: Any) -> int:
    if hasattr(row, "_mapping"):
        return int(next(iter(row._mapping.values())))
    if isinstance(row, tuple):
        return int(row[0])
    return int(row)


def _column_key(column: Any) -> str:
    key = getattr(column, "key", None)
    if key:
        return str(key)
    name = getattr(column, "name", None)
    if name:
        return str(name)
    raise WriteCompileError(f"Cannot resolve column key for {column!r}")


def _fk_column_key(nmap: Any) -> str:
    if nmap.fk_column is None:
        raise WriteCompileError(
            f"Nested field {nmap.semantic_field!r} requires fk_column for cascade "
            f"{nmap.cascade.value!r}"
        )
    return _column_key(nmap.fk_column)


def _identity_value(mapper_cls: type[Any], instance: OntoModel) -> Any:
    identity = mapper_cls.identity_field
    return getattr(instance, identity, None)


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
        col_key = _column_key(cmap.column)
        value = getattr(instance, field_name)
        if field_name == mapper_cls.identity_field and value is None:
            continue
        values[col_key] = value
    return values


def _snapshot_nested_identity(
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


def _delete_plan_for_identity(
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
            where={_column_key(identity_col.column): identity_value},
        ),
    )


def _compile_nested(
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
        old_nested_id = _snapshot_nested_identity(snapshot, field_name, nmap.nested_mapper)

        if policy is CascadePolicy.IGNORE:
            continue

        if nested_value is None:
            if policy is CascadePolicy.LINK:
                fk_key = _fk_column_key(nmap)
                fk_updates[fk_key] = None
            elif policy is CascadePolicy.REPLACE and not is_new and old_nested_id is not None:
                nested_deletes.append(
                    (field_name, _delete_plan_for_identity(nmap.nested_mapper, old_nested_id))
                )
                fk_updates[_fk_column_key(nmap)] = None
            continue

        if policy is CascadePolicy.LINK:
            nested_id = _identity_value(nmap.nested_mapper, nested_value)
            if nested_id is None:
                raise WriteCompileError(
                    f"Nested {field_name!r} requires an identity for cascade=link"
                )
            fk_updates[_fk_column_key(nmap)] = nested_id
            continue

        new_nested_id = _identity_value(nmap.nested_mapper, nested_value)
        if (
            policy is CascadePolicy.REPLACE
            and not is_new
            and old_nested_id is not None
            and old_nested_id != new_nested_id
        ):
            nested_deletes.append(
                (field_name, _delete_plan_for_identity(nmap.nested_mapper, old_nested_id))
            )

        nested_partial = None
        nested_snapshot = None
        if snapshot is not None:
            nested_raw = snapshot.get(field_name)
            if isinstance(nested_raw, dict):
                nested_snapshot = nested_raw
        if partial_fields is not None and field_name in partial_fields:
            nested_partial = set(nested_value.model_fields_set)
        nested_plan = compile_save_plan(
            nmap.nested_mapper,
            nested_value,
            partial_fields=nested_partial,
            snapshot=nested_snapshot,
        )
        nested_plans.append((field_name, nested_plan))
        if new_nested_id is not None:
            fk_updates[_fk_column_key(nmap)] = new_nested_id

    return nested_plans, nested_deletes, fk_updates


def _compile_collections(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    partial_fields: set[str] | None,
) -> list[CollectionWritePlan]:
    plans: list[CollectionWritePlan] = []
    for field_name, cmap in mapper_cls.collection_maps.items():
        if partial_fields is not None and field_name not in partial_fields:
            continue
        if cmap.cascade is CascadePolicy.IGNORE:
            continue
        items = getattr(instance, field_name, None) or []
        nested_writes: list[WritePlan] = []
        if cmap.cascade in (CascadePolicy.UPSERT, CascadePolicy.REPLACE):
            for item in items:
                item_new = _identity_value(cmap.nested_mapper, item) is None
                nested_writes.append(
                    compile_save_plan(
                        cmap.nested_mapper,
                        item,
                        is_new=item_new,
                    )
                )
        elif cmap.cascade is CascadePolicy.LINK:
            for item in items:
                if _identity_value(cmap.nested_mapper, item) is None:
                    raise WriteCompileError(
                        f"Collection item in {field_name!r} requires an identity for cascade=link"
                    )
        plans.append(
            CollectionWritePlan(
                field_name=field_name,
                policy=cmap.cascade.value,
                items=list(items),
                nested_writes=nested_writes,
            )
        )
    return plans


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
        where = {_column_key(identity_col.column): getattr(instance, identity)}

    nested_plans, nested_deletes, fk_updates = _compile_nested(
        mapper_cls,
        instance,
        partial_fields=partial_fields if not new else None,
        snapshot=snapshot,
        is_new=new,
    )

    collection_plans = _compile_collections(
        mapper_cls,
        instance,
        partial_fields=partial_fields if not new else None,
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


def compile_delete_plan(mapper_cls: type[Any], instance: OntoModel) -> DeletePlan:
    """Build a DeletePlan for delete() — root row only."""
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

    return DeletePlan(
        mapper_cls=mapper_cls,
        root=TableWrite(
            table=root_table,
            where={_column_key(identity_col.column): identity_value},
        ),
    )
