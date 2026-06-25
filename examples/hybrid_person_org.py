"""Hybrid SQL + graph demo — CRUD in SQL with automatic graph sync."""

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from ontosql import OntoSession
from ontosql.import_ import import_from_jsonld
from ontosql.shacl import shapes_from_mapper, validate_instance
from ontosql.sync import StoreSyncTarget
from ontosql.sync.materialize import materialize_find
from tests.models import OrgRow, Organization, OrganizationMap, Person, PersonMap, PersonRow


def main() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()

    graph_target = StoreSyncTarget()

    with OntoSession(
        engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=graph_target,
        graph_sync_mode="replace",
    ) as session:
        ada = session.get(Person, id=1)
        assert ada is not None
        print(f"SQL read: {ada.name}")

        ada.name = "Ada L. Lovelace"
        ada = session.save(ada)
        print(f"SQL updated: {ada.name}")

        print(f"Graph triples after save: {len(graph_target.graph)}")

        materialized = materialize_find(session, Person)
        print(f"Materialized graph: {len(materialized)} triples")

        doc = ada.to_jsonld()
        imported = import_from_jsonld(doc, PersonMap)
        print(f"Import round-trip: {imported.name}")

        shapes = shapes_from_mapper(PersonMap)
        try:
            report = validate_instance(ada, PersonMap, shapes=shapes)
            print(f"SHACL validation: conforms={report.conforms}")
        except ImportError:
            print("SHACL validation skipped (install ontosql[shacl])")


if __name__ == "__main__":
    main()
