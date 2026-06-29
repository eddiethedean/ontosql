"""Contract test: documented public API symbols are importable."""

from __future__ import annotations

import importlib


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
    assert "GraphSyncFailure" not in ontosql.__all__


def test_graph_sync_failure_from_session_only() -> None:
    import ontosql
    from ontosql.session import GraphSyncFailure

    assert GraphSyncFailure is not None
    assert "GraphSyncFailure" not in ontosql.__all__


def test_export_subpackage_matches_all() -> None:
    from ontosql import export as export_pkg

    expected = {
        "instance_to_graph",
        "instance_to_jsonld",
        "instance_to_rdf",
        "instances_to_graph",
        "instances_to_jsonld",
        "instances_to_rdf",
        "write_instance_to_graph",
    }
    assert expected <= set(export_pkg.__all__)


def test_import_subpackage_matches_all() -> None:
    from ontosql import import_ as import_pkg

    expected = {
        "DEFAULT_MAX_NESTING_DEPTH",
        "OntoImportError",
        "UNTRUSTED_DEFAULT_MAX_BYTES",
        "UNTRUSTED_DEFAULT_MAX_TRIPLES",
        "find_subjects_by_type",
        "graph_to_instance",
        "import_from_jsonld",
        "import_from_rdf",
        "load_graph",
        "load_graph_from_jsonld",
        "subject_iri_from_jsonld",
    }
    assert expected <= set(import_pkg.__all__)


def test_mapping_subpackage_functions() -> None:
    from ontosql.mapping import collection, column, computed, nested

    assert all(callable(fn) for fn in (column, nested, computed, collection))


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
    pytest.importorskip("pyshacl")

    from ontosql.shacl import shapes_from_mapper, validate_instance

    assert callable(shapes_from_mapper)
    assert callable(validate_instance)


def test_fastapi_extra() -> None:
    pytest = __import__("pytest")
    pytest.importorskip("fastapi")

    from ontosql.fastapi import (
        DEFAULT_MAX_BODY_BYTES,
        AsyncSessionDep,
        JSONLDResponse,
        OntoRouter,
        RDFResponse,
        SessionDep,
        TurtleResponse,
        get_async_onto_session,
        get_onto_session,
        negotiate_onto_response,
        onto_async_session_lifespan,
        onto_session_lifespan,
    )

    assert OntoRouter is not None
    assert DEFAULT_MAX_BODY_BYTES == 64 * 1024
    assert callable(get_onto_session)
    assert callable(get_async_onto_session)
    assert callable(onto_session_lifespan)
    assert callable(onto_async_session_lifespan)
    assert callable(negotiate_onto_response)
    assert SessionDep is not None
    assert AsyncSessionDep is not None
    for cls in (JSONLDResponse, RDFResponse, TurtleResponse):
        assert cls is not None


def test_fastapi_router_module_exports() -> None:
    mod = importlib.import_module("ontosql.fastapi.router")
    assert hasattr(mod, "DEFAULT_MAX_BODY_BYTES")
    assert hasattr(mod, "OntoRouter")
