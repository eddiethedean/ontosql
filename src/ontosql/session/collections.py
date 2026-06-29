"""Attach batched collection fields to hydrated instances."""

from __future__ import annotations

from typing import Any

from ontosql.compile.collection import compile_collection_load, group_collection_rows
from ontosql.semantic.model import OntoModel


def attach_collections(
    session: Any,
    mapper_cls: type[Any],
    instances: list[OntoModel],
) -> None:
    """Batch-load collection fields for hydrated instances (sync session)."""
    if not instances or not mapper_cls.collection_maps:
        return
    identity_field = mapper_cls.identity_field
    root_ids = [getattr(inst, identity_field) for inst in instances]
    root_ids = [rid for rid in root_ids if rid is not None]
    if not root_ids:
        return

    for field_name in mapper_cls.collection_maps:
        for inst in instances:
            setattr(inst, field_name, [])
        stmt, projections, _, _ = compile_collection_load(mapper_cls, field_name, root_ids)
        rows = session.exec(stmt).all()
        grouped = group_collection_rows(mapper_cls, field_name, projections, rows)
        for inst in instances:
            rid = getattr(inst, identity_field)
            if rid is not None and rid in grouped:
                setattr(inst, field_name, grouped[rid])


async def attach_collections_async(
    session: Any,
    mapper_cls: type[Any],
    instances: list[OntoModel],
) -> None:
    """Batch-load collection fields for hydrated instances (async session)."""
    if not instances or not mapper_cls.collection_maps:
        return
    identity_field = mapper_cls.identity_field
    root_ids = [getattr(inst, identity_field) for inst in instances]
    root_ids = [rid for rid in root_ids if rid is not None]
    if not root_ids:
        return

    for field_name in mapper_cls.collection_maps:
        for inst in instances:
            setattr(inst, field_name, [])
        stmt, projections, _, _ = compile_collection_load(mapper_cls, field_name, root_ids)
        result = await session.execute(stmt)
        rows = result.all()
        grouped = group_collection_rows(mapper_cls, field_name, projections, rows)
        for inst in instances:
            rid = getattr(inst, identity_field)
            if rid is not None and rid in grouped:
                setattr(inst, field_name, grouped[rid])
