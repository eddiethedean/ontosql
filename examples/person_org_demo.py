"""Full CRUD round-trip for Person / Organization through OntoSQL."""

from __future__ import annotations

import _bootstrap  # noqa: F401 — adds examples/ to sys.path
from sqlmodel import create_engine

from models import Organization, OrganizationMap, Person, PersonMap, seed_demo_data
from ontosql import OntoSession


def main() -> None:
    engine = create_engine("sqlite://")
    seed_demo_data(engine)

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
