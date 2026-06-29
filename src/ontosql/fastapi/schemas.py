"""Dynamic Pydantic body models for OntoRouter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model
from pydantic_core import PydanticUndefined

from ontosql.semantic.model import OntoModel


def _create_field_spec(field_info: Any) -> tuple[Any, Any]:
    """Map FieldInfo to create_model (annotation, default) preserving required fields."""
    if field_info.is_required():
        return field_info.annotation, ...
    if field_info.default is not PydanticUndefined:
        return field_info.annotation, field_info.default
    if field_info.default_factory is not None:
        return field_info.annotation, field_info.default_factory
    return field_info.annotation, None


def create_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        if name == identity_field:
            annotation = field_info.annotation | None  # type: ignore[operator]
            fields[name] = (annotation, None)
            continue
        fields[name] = _create_field_spec(field_info)
    return create_model(f"{entity_type.__name__}Create", **fields)  # type: ignore[call-overload]


def patch_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        if name == identity_field:
            continue
        fields[name] = (field_info.annotation | None, None)  # type: ignore[operator]
    return create_model(f"{entity_type.__name__}Patch", **fields)  # type: ignore[call-overload]
