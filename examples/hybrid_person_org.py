"""Hybrid SQL + graph demo — CRUD in SQL with automatic graph sync."""

from __future__ import annotations

import _bootstrap  # noqa: F401
from sqlmodel import create_engine

from models import OrganizationMap, Person, PersonMap, seed_demo_data
from ontosql import OntoSession
from ontosql.import_ import import_from_jsonld
from ontosql.shacl import shapes_from_mapper, validate_instance
from ontosql.sync import StoreSyncTarget, materialize_find


def main() -> None:
    engine = create_engine("sqlite://")
    seed_demo_data(engine)

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

    print(f"Graph triples after commit: {len(graph_target.graph)}")

    with OntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
        ada = session.get(Person, id=1)
        assert ada is not None
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
