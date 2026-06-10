"""Full CRUD round-trip for Person / Organization through OntoSQL 0.3."""

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from ontosql import OntoSession
from tests.models import OrgRow, Organization, OrganizationMap, Person, PersonMap, PersonRow


def main() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()

    with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
        ada = session.get(Person, id=1)
        assert ada is not None
        print(f"Read: {ada.name} works for {ada.employer.name if ada.employer else 'nobody'}")

        new_org = session.save(Organization(id=20, name="New Lab"))
        print(f"Created org: {new_org.name}")

        solo = session.save(Person.model_construct(name="Grace Hopper", id=None))
        print(f"Created person id={solo.id}")

        solo.name = "Grace M. Hopper"
        session.save(solo)
        solo = session.get(Person, id=solo.id)
        assert solo is not None
        print(f"Updated: {solo.name}")

        solo.employer = new_org
        session.save(solo)
        reloaded = session.get(Person, id=solo.id)
        assert reloaded is not None and reloaded.employer is not None
        print(f"Linked employer: {reloaded.employer.name}")

        session.delete(reloaded)
        assert session.get(Person, id=solo.id) is None
        print("Deleted person")


if __name__ == "__main__":
    main()
