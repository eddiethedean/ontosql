"""OpenAPI schema enrichment for semantic entities."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from ontosql.semantic.model import OntoModel


def enrich_openapi_schema(app: FastAPI, entity_types: list[type[OntoModel]]) -> dict[str, Any]:
    """Return OpenAPI schema with semantic hints for registered OntoModel types."""
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for entity in entity_types:
        name = entity.__name__
        type_iri = getattr(entity, "type_iri", None)
        ctx = getattr(entity, "jsonld_context", None) or getattr(entity, "context", None)
        if name not in components:
            components[name] = {"type": "object", "title": name}
        entry = components[name]
        if type_iri:
            entry["x-ontosql-type-iri"] = type_iri
        if ctx:
            entry["description"] = f"JSON-LD @context: {ctx!r}"
            entry["x-ontosql-context"] = ctx
        entry.setdefault("properties", {})
    return schema


def install_onto_openapi(app: FastAPI, entity_types: list[type[OntoModel]]) -> None:
    """Replace app.openapi with semantic-enriched schema generation."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = enrich_openapi_schema(app, entity_types)
        return app.openapi_schema

    app.openapi = custom_openapi  # ty: ignore[invalid-assignment]
