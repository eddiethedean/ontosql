"""Contract test: documented public API symbols are importable."""

from __future__ import annotations


def test_root_package_exports() -> None:
    import ontosql

    expected = {
        "AsyncOntoSession",
        "CascadePolicy",
        "GraphSyncError",
        "GraphSyncMode",
        "Map",
        "OntoImportError",
        "OntoMapper",
        "OntoModel",
        "OntoSession",
        "Page",
        "PrefixRegistry",
        "__version__",
        "onto_property",
        "paginate",
        "paginate_async",
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
        write_instance_to_graph,
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
            write_instance_to_graph,
        )
    )


def test_import_subpackage() -> None:
    from ontosql.import_ import (
        OntoImportError,
        graph_to_instance,
        import_from_jsonld,
        import_from_rdf,
        load_graph,
    )

    assert all(
        callable(fn) for fn in (import_from_jsonld, import_from_rdf, graph_to_instance, load_graph)
    )
    assert issubclass(OntoImportError, Exception)


def test_sync_subpackage() -> None:
    from ontosql.sync import (
        GraphSyncMode,
        GraphSyncTarget,
        StoreSyncTarget,
        materialize_find,
        materialize_find_async,
        push_instance,
        remove_instance,
    )

    assert all(
        callable(fn)
        for fn in (
            push_instance,
            remove_instance,
            materialize_find,
            materialize_find_async,
        )
    )
    assert StoreSyncTarget is not None
    assert GraphSyncTarget is not None
    assert GraphSyncMode is not None


def test_query_subpackage() -> None:
    from ontosql.query import FieldPath, FieldRef

    assert FieldRef is not None
    assert FieldPath is not None


def test_compile_package_not_reexported() -> None:
    import ontosql.compile

    assert ontosql.compile.__all__ == []


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
        AsyncSessionDep,
        OntoRouter,
        SessionDep,
        get_async_onto_session,
        get_onto_session,
        onto_async_session_lifespan,
        onto_session_lifespan,
    )

    assert OntoRouter is not None
    assert callable(get_onto_session)
    assert callable(get_async_onto_session)
    assert callable(onto_session_lifespan)
    assert callable(onto_async_session_lifespan)
    assert SessionDep is not None
    assert AsyncSessionDep is not None
