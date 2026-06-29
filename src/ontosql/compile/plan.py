"""Compiled select and write plan types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.sql import Select

from ontosql.mapping.cascade import CascadePolicy


@dataclass
class ColumnProjection:
    """A selected column with a unique label."""

    label: str
    semantic_field: str
    column: Any
    source: str  # "root" or nested semantic field name


@dataclass
class SelectPlan:
    """Result of compiling a mapper to a SELECT."""

    select: Select[Any]
    projections: list[ColumnProjection] = field(default_factory=list)
    nested_projections: dict[str, list[ColumnProjection]] = field(default_factory=dict)
    mapper_cls: type[Any] | None = None

    def label_for(self, semantic_field: str, nested: str | None = None) -> str:
        if nested:
            for proj in self.nested_projections.get(nested, []):
                if proj.semantic_field == semantic_field:
                    return proj.label
        for proj in self.projections:
            if proj.semantic_field == semantic_field:
                return proj.label
        raise KeyError(f"No projection for field {semantic_field!r}")


@dataclass
class TableWrite:
    """Column values and optional identity predicate for one physical table."""

    table: Any
    values: dict[str, Any] = field(default_factory=dict)
    where: dict[str, Any] | None = None


@dataclass
class CollectionWritePlan:
    """Bridge-table sync for a collection field on save."""

    field_name: str
    policy: CascadePolicy
    items: list[Any]
    nested_writes: list[Any] = field(default_factory=list)
    member_deletes: list[DeletePlan] = field(default_factory=list)


@dataclass
class WritePlan:
    """Insert or update plan for one semantic entity."""

    mapper_cls: type[Any]
    operation: Literal["insert", "update"]
    root: TableWrite
    nested: list[tuple[str, WritePlan]] = field(default_factory=list)
    nested_deletes: list[tuple[str, DeletePlan]] = field(default_factory=list)
    fk_updates: dict[str, Any] = field(default_factory=dict)
    collections: list[CollectionWritePlan] = field(default_factory=list)


@dataclass
class DeletePlan:
    """Delete plan for one semantic entity (root row and optional nested cascades)."""

    mapper_cls: type[Any]
    root: TableWrite
    nested_deletes: list[tuple[str, DeletePlan]] = field(default_factory=list)
