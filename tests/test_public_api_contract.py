"""Contract test: documented public API symbols are importable."""

from __future__ import annotations


def test_root_package_exports() -> None:
    import ontosql

    expected = {
        "AsyncOntoSession",
        "CascadePolicy",
        "Map",
        "OntoMapper",
        "OntoModel",
        "OntoSession",
        "Page",
        "PrefixRegistry",
        "__version__",
        "onto_property",
        "paginate",
    }
    assert expected <= set(ontosql.__all__)


def test_export_subpackage() -> None:
    from ontosql.export import (
        instance_to_graph,
        instance_to_jsonld,
        instance_to_rdf,
        instances_to_graph,
        instances_to_jsonld,
        instances_to_rdf,
    )

    assert all(
        callable(fn)
        for fn in (
            instance_to_graph,
            instance_to_jsonld,
            instance_to_rdf,
            instances_to_graph,
            instances_to_jsonld,
            instances_to_rdf,
        )
    )


def test_import_subpackage() -> None:
    from ontosql.import_ import graph_to_instance, import_from_jsonld, import_from_rdf

    assert all(callable(fn) for fn in (import_from_jsonld, import_from_rdf, graph_to_instance))


def test_sync_subpackage() -> None:
    from ontosql.sync import (
        StoreSyncTarget,
        materialize_entity,
        materialize_find,
        push_instance,
        remove_instance,
    )

    assert all(
        callable(fn)
        for fn in (
            push_instance,
            remove_instance,
            materialize_find,
            materialize_entity,
        )
    )
    assert StoreSyncTarget is not None


def test_query_subpackage() -> None:
    from ontosql.query import FieldPath, FieldRef

    assert FieldRef is not None
    assert FieldPath is not None


def test_shacl_extra() -> None:
    pytest = __import__("pytest")
    pyshacl = pytest.importorskip("pyshacl")
    assert pyshacl is not None

    from ontosql.shacl import shapes_from_mapper, validate_instance

    assert callable(shapes_from_mapper)
    assert callable(validate_instance)


def test_fastapi_extra() -> None:
    pytest = __import__("pytest")
    fastapi = pytest.importorskip("fastapi")
    assert fastapi is not None

    from ontosql.fastapi import (
        OntoRouter,
        get_async_onto_session,
        get_onto_session,
        onto_session_lifespan,
    )

    assert OntoRouter is not None
    assert callable(get_onto_session)
    assert callable(get_async_onto_session)
    assert callable(onto_session_lifespan)
