"""FastAPI CRUD over Person / Organization via OntoRouter (~30 lines)."""

from __future__ import annotations

import _bootstrap  # noqa: F401
from fastapi import FastAPI
from sqlmodel import create_engine

from models import Organization, OrganizationMap, Person, PersonMap, seed_demo_data
from ontosql.fastapi.deps import onto_session_lifespan
from ontosql.fastapi.router import OntoRouter


def main() -> None:
    engine = create_engine("sqlite://")
    seed_demo_data(engine)

    app = FastAPI(title="Person Org API")
    onto_session_lifespan(app, engine, [PersonMap, OrganizationMap])
    router = OntoRouter(maps=[PersonMap, OrganizationMap])
    router.register(Person)
    router.register(Organization)
    router.include_in(app)

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
