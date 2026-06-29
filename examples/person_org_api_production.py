"""Production-oriented FastAPI wiring: async session, validation, body limits.

Contrast with ``person_org_api.py`` (demo ``OntoRouter`` + sync session).
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
from fastapi import FastAPI, HTTPException, Request, status
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, SQLModel

from models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow
from ontosql.fastapi.deps import AsyncSessionDep, onto_async_session_lifespan
from ontosql.fastapi.negotiate import negotiate_onto_response

MAX_BODY_BYTES = 64 * 1024


def _seed_sync(connection) -> None:
    with Session(bind=connection) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()


def create_app() -> FastAPI:
    app = FastAPI(title="Person Org API (production pattern)")

    @app.on_event("startup")
    async def _startup() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        app.state._engine = engine
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await conn.run_sync(_seed_sync)
        onto_async_session_lifespan(app, engine, [PersonMap, OrganizationMap])

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await app.state._engine.dispose()

    @app.get("/person/{person_id}")
    async def get_person(person_id: int, request: Request, session: AsyncSessionDep) -> object:
        person = await session.get(Person, id=person_id)
        if person is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return negotiate_onto_response(request, person)

    @app.post("/person", status_code=status.HTTP_201_CREATED)
    async def create_person(request: Request, session: AsyncSessionDep) -> object:
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Body exceeds {MAX_BODY_BYTES} bytes",
            )
        data = await request.json()
        person = Person.model_validate(data)
        saved = await session.save(person)
        response = negotiate_onto_response(request, saved)
        response.status_code = status.HTTP_201_CREATED
        return response

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
