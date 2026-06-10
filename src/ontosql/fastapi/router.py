"""Auto-generated CRUD routes for OntoModel entities."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, create_model

from ontosql.fastapi.deps import SessionDep
from ontosql.fastapi.negotiate import negotiate_onto_response
from ontosql.fastapi.openapi import install_onto_openapi
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel
from ontosql.session.pagination import paginate


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


def _patch_body_model(entity_type: type[OntoModel]) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for name, field_info in entity_type.model_fields.items():
        fields[name] = (field_info.annotation | None, None)  # type: ignore[operator]
    return create_model(f"{entity_type.__name__}Patch", **fields)  # type: ignore[call-overload]


class OntoRouter:
    """Register CRUD routes for OntoModel entities with content negotiation."""

    def __init__(
        self,
        *,
        maps: list[type[Any]],
        prefix: str = "/onto",
    ) -> None:
        self.maps = maps
        self.prefix = prefix.rstrip("/")
        self.router = APIRouter()
        self._entities: list[type[OntoModel]] = []

    def register(self, entity_type: type[OntoModel]) -> None:
        """Add GET/POST/PATCH/DELETE routes for one entity type."""
        if entity_type in self._entities:
            return
        self._entities.append(entity_type)
        name = _entity_route_name(entity_type)
        mapper_cls = _mapper_for(self.maps, entity_type)
        _ = _create_body_model(entity_type, identity_field=mapper_cls.identity_field)
        _ = _patch_body_model(entity_type)

        @self.router.get(f"/{name}/{{entity_id}}")
        def get_one(entity_id: int, request: Request, session: SessionDep) -> Any:
            instance = session.get(entity_type, id=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            return negotiate_onto_response(request, instance)

        @self.router.get(f"/{name}")
        def list_entities(
            request: Request,
            session: SessionDep,
            limit: int = Query(20, le=100),
            offset: int = 0,
        ) -> Any:
            page = paginate(session, entity_type, limit=limit, offset=offset)
            payload: list[Any] | dict[str, Any]
            if request.headers.get("accept", "").startswith("application/ld+json"):
                payload = {
                    "@context": getattr(entity_type, "jsonld_context", {}),
                    "@graph": [item.to_jsonld() for item in page.items],
                }
            else:
                payload = [item.model_dump() for item in page.items]
            return negotiate_onto_response(request, payload)

        @self.router.post(f"/{name}", status_code=status.HTTP_201_CREATED)
        async def create_entity(request: Request, session: SessionDep) -> Any:
            data = await request.json()
            if mapper_cls.identity_field not in data:
                data[mapper_cls.identity_field] = None
            instance = entity_type.model_construct(**data)
            saved = session.save(instance)
            response = negotiate_onto_response(request, saved)
            response.status_code = status.HTTP_201_CREATED
            return response

        @self.router.patch(f"/{name}/{{entity_id}}")
        async def patch_entity(entity_id: int, request: Request, session: SessionDep) -> Any:
            instance = session.get(entity_type, id=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            data = await request.json()
            updated = instance.model_copy(update=data)
            saved = session.save(updated)
            return negotiate_onto_response(request, saved)

        @self.router.delete(f"/{name}/{{entity_id}}", status_code=status.HTTP_204_NO_CONTENT)
        def delete_entity(entity_id: int, session: SessionDep) -> None:
            instance = session.get(entity_type, id=entity_id)
            if instance is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            session.delete(instance)

    def include_in(self, app: Any, *, prefix: str | None = None) -> None:
        """Mount routes on a FastAPI app and install semantic OpenAPI enrichment."""
        mount_prefix = prefix if prefix is not None else self.prefix
        app.include_router(self.router, prefix=mount_prefix)
        install_onto_openapi(app, self._entities)
