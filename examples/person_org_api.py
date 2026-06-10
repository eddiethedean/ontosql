"""FastAPI CRUD over Person / Organization via OntoRouter (~30 lines)."""

from __future__ import annotations

from fastapi import FastAPI
from sqlmodel import Session, SQLModel, create_engine

from ontosql.fastapi.deps import onto_session_lifespan
from ontosql.fastapi.router import OntoRouter
from tests.models import OrgRow, Organization, OrganizationMap, Person, PersonMap, PersonRow


def main() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()

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
