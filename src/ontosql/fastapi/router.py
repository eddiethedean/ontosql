"""Auto-generated CRUD routes for OntoModel entities."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, create_model

from ontosql.fastapi.deps import SessionDep
from ontosql.fastapi.negotiate import negotiate_onto_response, parse_accept_mime
from ontosql.fastapi.openapi import install_onto_openapi
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.pagination import paginate

_HTTP_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)


def _entity_route_name(entity_type: type[OntoModel]) -> str:
    return entity_type.__name__.lower()


def _mapper_for(maps: list[type[Any]], entity_type: type[OntoModel]) -> type[Any]:
    registry = MapperRegistry()
    registry.register_many(maps)
    return registry.get(entity_type)


def _create_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        annotation = field_info.annotation
        if name == identity_field:
            annotation = annotation | None  # type: ignore[operator]
        fields[name] = (annotation, None)
    return create_model(f"{entity_type.__name__}Create", **fields)  # type: ignore[call-overload]


def _patch_body_model(entity_type: type[OntoModel], *, identity_field: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        if name == identity_field:
            continue
        fields[name] = (field_info.annotation | None, None)  # type: ignore[operator]
    return create_model(f"{entity_type.__name__}Patch", **fields)  # type: ignore[call-overload]


async def _read_json_body(request: Request, max_body_bytes: int | None) -> Any:
    if max_body_bytes is not None:
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > max_body_bytes:
            raise HTTPException(
                status_code=_HTTP_413,
                detail=f"Request body exceeds max_body_bytes={max_body_bytes}",
            )
        raw = await request.body()
        if len(raw) > max_body_bytes:
            raise HTTPException(
                status_code=_HTTP_413,
                detail=f"Request body exceeds max_body_bytes={max_body_bytes}",
            )
        return json.loads(raw)
    return await request.json()


def _instance_from_create(
    entity_type: type[OntoModel],
    validated: BaseModel,
    *,
    validate_entities: bool,
    identity_field: str,
) -> OntoModel:
    data = validated.model_dump()
    if validate_entities:
        probe = dict(data)
        if probe.get(identity_field) is None:
            probe[identity_field] = 0
        entity_type.model_validate(probe)
    return entity_type.model_construct(**data)


class OntoRouter:
    """Register CRUD routes for OntoModel entities with content negotiation.

    **Demo-grade** — no auth, rate limits, or async SQL. For production patterns see
    ``docs/guides/production-router.md`` and ``examples/person_org_api_production.py``.
    """

    def __init__(
        self,
        *,
        maps: list[type[Any]],
        prefix: str = "/onto",
        validate_entities: bool = False,
        max_body_bytes: int | None = None,
    ) -> None:
        self.maps = maps
        self.prefix = prefix.rstrip("/")
        self.validate_entities = validate_entities
        self.max_body_bytes = max_body_bytes
        self.router = APIRouter()
        self._entities: list[type[OntoModel]] = []

    def register(self, entity_type: type[OntoModel]) -> None:
        """Add GET/POST/PATCH/DELETE routes for one entity type."""
        if entity_type in self._entities:
            return
        self._entities.append(entity_type)
        name = _entity_route_name(entity_type)
        mapper_cls = _mapper_for(self.maps, entity_type)
        create_body_model = _create_body_model(
            entity_type, identity_field=mapper_cls.identity_field
        )
        patch_body_model = _patch_body_model(entity_type, identity_field=mapper_cls.identity_field)
        CreateBody = create_body_model
        PatchBody = patch_body_model
        validate_entities = self.validate_entities
        max_body_bytes = self.max_body_bytes

        @self.router.get(f"/{name}/{{entity_id}}")
        def get_one(entity_id: int, request: Request, session: SessionDep) -> Any:
            instance = session.get(entity_type, identity=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            return negotiate_onto_response(request, instance)

        @self.router.get(f"/{name}")
        def list_entities(
            request: Request,
            session: SessionDep,
            limit: int = Query(20, le=100),
            offset: int = Query(0, ge=0),
        ) -> Any:
            accept = request.headers.get("accept")
            chosen = parse_accept_mime(accept)
            if chosen is not None and chosen != "application/ld+json":
                from ontosql.export._formats import format_for_mime
                from ontosql.fastapi.negotiate import negotiate_graph_response
                from ontosql.sync import materialize_find

                if format_for_mime(chosen) is not None:
                    graph = materialize_find(session, entity_type, limit=limit, offset=offset)
                    return negotiate_graph_response(chosen, graph)

            page = paginate(session, entity_type, limit=limit, offset=offset)
            payload: list[Any] | dict[str, Any]
            if accept and accept.startswith("application/ld+json"):
                payload = {
                    "@context": getattr(entity_type, "jsonld_context", {}),
                    "@graph": [item.to_jsonld() for item in page.items],
                }
            else:
                payload = [item.model_dump() for item in page.items]
            return negotiate_onto_response(request, payload)

        @self.router.post(f"/{name}", status_code=status.HTTP_201_CREATED)
        async def create_entity(request: Request, session: SessionDep) -> Any:
            data = await _read_json_body(request, max_body_bytes)
            if mapper_cls.identity_field not in data:
                data[mapper_cls.identity_field] = None
            validated = CreateBody.model_validate(data)
            instance = _instance_from_create(
                entity_type,
                validated,
                validate_entities=validate_entities,
                identity_field=mapper_cls.identity_field,
            )
            saved = session.save(instance)
            response = negotiate_onto_response(request, saved)
            response.status_code = status.HTTP_201_CREATED
            return response

        @self.router.patch(f"/{name}/{{entity_id}}")
        async def patch_entity(entity_id: int, request: Request, session: SessionDep) -> Any:
            instance = session.get(entity_type, identity=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            data = await _read_json_body(request, max_body_bytes)
            identity_field = mapper_cls.identity_field
            if identity_field in data and data[identity_field] != entity_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot change {identity_field!r} via PATCH",
                )
            data.pop(identity_field, None)
            validated = PatchBody.model_validate(data)
            updated = instance.model_copy(update=validated.model_dump(exclude_unset=True))
            setattr(updated, identity_field, entity_id)
            if validate_entities:
                updated = entity_type.model_validate(updated.model_dump())
            saved = session.save(updated)
            return negotiate_onto_response(request, saved)

        @self.router.delete(f"/{name}/{{entity_id}}", status_code=status.HTTP_204_NO_CONTENT)
        def delete_entity(entity_id: int, session: SessionDep) -> None:
            instance = session.get(entity_type, identity=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            session.delete(instance)

    def include_in(self, app: Any, *, prefix: str | None = None) -> None:
        """Mount routes on a FastAPI app and install semantic OpenAPI enrichment."""
        mount_prefix = prefix if prefix is not None else self.prefix
        app.include_router(self.router, prefix=mount_prefix)
        install_onto_openapi(app, self._entities)
