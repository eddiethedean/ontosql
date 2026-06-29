"""Dynamic Pydantic body models for OntoRouter."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

from ontosql.semantic.model import OntoModel


def create_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        annotation = field_info.annotation
        if name == identity_field:
            annotation = annotation | None  # type: ignore[operator]
        fields[name] = (annotation, None)
    return create_model(f"{entity_type.__name__}Create", **fields)  # type: ignore[call-overload]


def patch_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        if name == identity_field:
            continue
        fields[name] = (field_info.annotation | None, None)  # type: ignore[operator]
    return create_model(f"{entity_type.__name__}Patch", **fields)  # type: ignore[call-overload]
