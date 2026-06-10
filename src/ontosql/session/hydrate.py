"""Hydrate SQL rows into semantic model instances."""

from __future__ import annotations

from typing import Any

from ontosql.compile.plan import SelectPlan
from ontosql.semantic.model import OntoModel


def _row_get(row: Any, label: str) -> Any:
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping[label]
    try:
        return row[label]
    except (KeyError, TypeError):
        return getattr(row, label, None)


def hydrate_first(plan: SelectPlan, result: Any) -> OntoModel | None:
    """Hydrate the first row from a SQLAlchemy result, or None if empty."""
    row = result.first()
    if row is None:
        return None
    return hydrate_row(plan, row)


def hydrate_row(plan: SelectPlan, row: Any) -> OntoModel:
    """Build a semantic instance from a result row."""
    mapper_cls = plan.mapper_cls
    if mapper_cls is None:
        raise ValueError("SelectPlan has no mapper_cls")
    entity_cls = mapper_cls.entity

    data: dict[str, Any] = {}
    for proj in plan.projections:
        data[proj.semantic_field] = _row_get(row, proj.label)

    for nested_field, nested_projs in plan.nested_projections.items():
        nested_mapper = mapper_cls.nested_maps[nested_field].nested_mapper
        nested_entity = nested_mapper.entity
        nested_data: dict[str, Any] = {}
        any_value = False
        for proj in nested_projs:
            val = _row_get(row, proj.label)
            nested_data[proj.semantic_field] = val
            if val is not None:
                any_value = True
        if any_value:
            identity = nested_mapper.identity_field
            if nested_data.get(identity) is None:
                data[nested_field] = None
            else:
                data[nested_field] = nested_entity(**nested_data)
        else:
            data[nested_field] = None

    return entity_cls(**data)
