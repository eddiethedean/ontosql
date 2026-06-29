"""Compile semantic queries to SQLAlchemy SELECT statements."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.sql import Select

from ontosql.compile.cache import select_skeleton, skeleton_to_plan_parts
from ontosql.compile.plan import SelectPlan
from ontosql.query.expr import AndExpr, FieldPath, FieldRef, OrderBy, OrExpr, compile_expr
from ontosql.semantic.model import parse_iri_id


def _column_for_field(mapper_cls: type[Any], field_ref: FieldRef | FieldPath) -> Any:
    if isinstance(field_ref, FieldPath):
        if len(field_ref.parts) == 1:
            name = field_ref.parts[0]
            if name in mapper_cls.column_maps:
                return mapper_cls.column_maps[name].column
            if name in mapper_cls.computed_maps:
                return mapper_cls.computed_maps[name].expression
            raise KeyError(f"Field {name!r} is not a column on mapper {mapper_cls.__name__}")
        nested_field = field_ref.parts[0]
        if nested_field not in mapper_cls.nested_maps:
            raise KeyError(f"Nested field {nested_field!r} is not on mapper {mapper_cls.__name__}")
        nested_mapper = mapper_cls.nested_maps[nested_field].nested_mapper
        tail = FieldPath(nested_mapper.entity, field_ref.parts[1:])
        return _column_for_field(nested_mapper, tail)

    name = field_ref.field_name
    if name in mapper_cls.column_maps:
        return mapper_cls.column_maps[name].column
    if name in mapper_cls.computed_maps:
        return mapper_cls.computed_maps[name].expression
    raise KeyError(f"Field {name!r} is not a column on mapper {mapper_cls.__name__}")


def _order_column(mapper_cls: type[Any], order_by: Any) -> Any:
    if isinstance(order_by, OrderBy):
        col = _column_for_field(mapper_cls, order_by.field)
        return col.desc() if order_by.desc else col
    return _column_for_field(mapper_cls, order_by)


def compile_select_plan(
    mapper_cls: type[Any],
    *,
    where: Any | None = None,
    order_by: Any | None = None,
    limit: int | None = None,
    offset: int | None = None,
    id_value: Any | None = None,
    iri: str | None = None,
) -> SelectPlan:
    """Build a SelectPlan for find or get."""
    skeleton = select_skeleton(mapper_cls)
    projections, nested_projections, columns, from_clause = skeleton_to_plan_parts(skeleton)

    stmt: Select[Any] = select(*columns).select_from(from_clause)

    if id_value is not None:
        identity = mapper_cls.identity_field
        stmt = stmt.where(mapper_cls.column_maps[identity].column == id_value)
    elif iri is not None:
        parsed = parse_iri_id(iri, mapper_cls.entity)
        if parsed is None:
            raise ValueError(f"Cannot parse IRI {iri!r} for {mapper_cls.entity.__name__}")
        identity = mapper_cls.identity_field
        stmt = stmt.where(mapper_cls.column_maps[identity].column == parsed)

    if where is not None:
        if isinstance(where, (AndExpr, OrExpr)):
            clause = compile_expr(where, lambda ref: _column_for_field(mapper_cls, ref))
        else:
            clause = compile_expr(where, lambda ref: _column_for_field(mapper_cls, ref))
        stmt = stmt.where(clause)

    if order_by is not None:
        stmt = stmt.order_by(_order_column(mapper_cls, order_by))

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    return SelectPlan(
        select=stmt,
        projections=projections,
        nested_projections=nested_projections,
        mapper_cls=mapper_cls,
    )


def compile_count_statement(
    mapper_cls: type[Any],
    *,
    where: Any | None = None,
    id_value: Any | None = None,
    iri: str | None = None,
) -> Any:
    """Build a SELECT COUNT(*) using the same filters as compile_select_plan."""
    plan = compile_select_plan(
        mapper_cls,
        where=where,
        id_value=id_value,
        iri=iri,
    )
    return select(func.count()).select_from(plan.select.subquery())
