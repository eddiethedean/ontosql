"""Collection field cascade compilation."""

from __future__ import annotations

from typing import Any

from ontosql.compile.errors import WriteCompileError
from ontosql.compile.nested_write import delete_plan_for_identity, identity_value
from ontosql.compile.plan import CollectionWritePlan, DeletePlan, WritePlan
from ontosql.mapping.cascade import CascadePolicy
from ontosql.semantic.model import OntoModel


def snapshot_collection_ids(
    snapshot: dict[str, Any] | None,
    field_name: str,
    nested_mapper: type[Any],
) -> set[Any]:
    if snapshot is None:
        return set()
    raw_items = snapshot.get(field_name)
    if not isinstance(raw_items, list):
        return set()
    ids: set[Any] = set()
    identity_field = nested_mapper.identity_field
    for item in raw_items:
        if isinstance(item, dict):
            member_id = item.get(identity_field)
        else:
            member_id = getattr(item, identity_field, None)
        if member_id is not None:
            ids.add(member_id)
    return ids


def compile_collections(
    mapper_cls: type[Any],
    instance: OntoModel,
    *,
    partial_fields: set[str] | None,
    snapshot: dict[str, Any] | None = None,
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
            from ontosql.compile.save_plan import compile_save_plan

            for item in items:
                item_new = identity_value(cmap.nested_mapper, item) is None
                nested_writes.append(
                    compile_save_plan(
                        cmap.nested_mapper,
                        item,
                        is_new=item_new,
                    )
                )
        elif cmap.cascade is CascadePolicy.LINK:
            for item in items:
                if identity_value(cmap.nested_mapper, item) is None:
                    raise WriteCompileError(
                        f"Collection item in {field_name!r} requires an identity for cascade=link"
                    )
        member_deletes: list[DeletePlan] = []
        if cmap.cascade is CascadePolicy.REPLACE and snapshot is not None:
            old_ids = snapshot_collection_ids(snapshot, field_name, cmap.nested_mapper)
            new_ids = {
                identity_value(cmap.nested_mapper, item)
                for item in items
                if identity_value(cmap.nested_mapper, item) is not None
            }
            for removed_id in old_ids - new_ids:
                member_deletes.append(delete_plan_for_identity(cmap.nested_mapper, removed_id))
        plans.append(
            CollectionWritePlan(
                field_name=field_name,
                policy=cmap.cascade,
                items=list(items),
                nested_writes=nested_writes,
                member_deletes=member_deletes,
            )
        )
    return plans
