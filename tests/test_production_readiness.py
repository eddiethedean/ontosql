"""Production readiness: graph sync failures, session guards, import limits, router hardening."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ontosql import OntoSession
from ontosql.import_ import OntoImportError, import_from_rdf, load_graph
from ontosql.import_.hydrate import graph_to_instance
from ontosql.import_.parse import UNTRUSTED_DEFAULT_MAX_BYTES
from ontosql.session.graph_sync import GraphSyncError
from ontosql.sync import StoreSyncTarget
from tests.conftest import build_async_onto_test_app
from tests.models import Organization, OrganizationMap, Person, PersonMap

pytest.importorskip("fastapi")


def test_graph_sync_partial_push_preserves_queue(sync_engine) -> None:
    target = StoreSyncTarget()
    push_calls = {"n": 0}
    from ontosql.sync import push_instance as real_push

    def flaky_push(*args: Any, **kwargs: Any) -> None:
        push_calls["n"] += 1
        if push_calls["n"] > 1:
            raise RuntimeError("simulated graph push failure")
        real_push(*args, **kwargs)

    closed: OntoSession | None = None
    with (
        patch("ontosql.sync.push_instance", side_effect=flaky_push),
        pytest.raises(GraphSyncError, match="still queued"),
        OntoSession(
            sync_engine,
            maps=[PersonMap, OrganizationMap],
            graph_sync=target,
            graph_sync_mode="replace",
        ) as session,
    ):
        closed = session
        session.save(Person(id=70, name="First", employer=None))
        session.save(Person(id=71, name="Second", employer=None))

    assert closed is not None
    assert closed.graph_sync_pending
    assert len(closed.graph_sync_failures) == 1
    assert closed.graph_sync_failures[0].operation == "push"


def test_retry_graph_sync_after_partial_failure(sync_engine) -> None:
    target = StoreSyncTarget()
    session = OntoSession(
        sync_engine,
        maps=[PersonMap, OrganizationMap],
        graph_sync=target,
        graph_sync_mode="replace",
    )
    with (
        patch(
            "ontosql.sync.push_instance",
            side_effect=RuntimeError("simulated graph push failure"),
        ),
        pytest.raises(GraphSyncError),
        session,
    ):
        session.save(Person(id=72, name="Retry Me", employer=None))

    assert session.graph_sync_pending
    session.retry_graph_sync()
    assert not session.graph_sync_pending


def test_sync_session_requires_context_manager(sync_engine) -> None:
    session = OntoSession(sync_engine, maps=[PersonMap])
    with pytest.raises(RuntimeError, match="not active"):
        session.get(Person, identity=1)


def test_flush_preserves_pending_on_error(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        session.save(Person(id=80, name="Pending A", employer=None), flush_now=False)
        session.save(Person(id=81, name="Pending B", employer=None), flush_now=False)
        assert len(session._state.pending) == 2  # noqa: SLF001
        with (
            patch(
                "ontosql.session.sync.execute_write_plan",
                side_effect=[None, RuntimeError("write failed")],
            ),
            pytest.raises(RuntimeError, match="write failed"),
        ):
            session.flush()
        assert len(session._state.pending) == 1  # noqa: SLF001


def test_import_max_triples_raises() -> None:
    person = Person(id=1, name="Ada", employer=None)
    turtle = person.to_rdf(format="turtle")
    with pytest.raises(OntoImportError, match="max_triples"):
        import_from_rdf(turtle, PersonMap, format="turtle", max_triples=0)


def test_load_graph_max_bytes_raises() -> None:
    data = b"@prefix schema: <https://schema.org/> .\n"
    with pytest.raises(OntoImportError, match="max_bytes"):
        load_graph(data, format="turtle", max_bytes=10)


@pytest.fixture
def api_client(api_client_hardened: TestClient) -> TestClient:
    return api_client_hardened


def test_router_rejects_oversized_body(api_client: TestClient) -> None:
    huge = {"name": "x" * 500, "employer": None}
    resp = api_client.post("/onto/person", json=huge)
    assert resp.status_code == 413


def test_router_validate_entities_smoke(api_client: TestClient) -> None:
    resp = api_client.post("/onto/person", json={"name": "Validated", "employer": None})
    assert resp.status_code == 201


def test_router_rejects_invalid_content_length(api_client: TestClient) -> None:
    resp = api_client.post(
        "/onto/person",
        content=b'{"name": "x"}',
        headers={
            "Content-Type": "application/json",
            "Content-Length": "not-a-number",
        },
    )
    assert resp.status_code == 400


def test_load_graph_untrusted_default_max_bytes() -> None:
    data = b"x" * (UNTRUSTED_DEFAULT_MAX_BYTES + 1)
    with pytest.raises(OntoImportError, match="max_bytes"):
        load_graph(data, format="turtle", untrusted=True)


def test_graph_to_instance_max_nesting_depth() -> None:
    from ontosql.registry import PrefixRegistry
    from ontosql.semantic.model import build_instance_iri

    person = Person(
        id=1,
        name="Ada",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    turtle = person.to_rdf(format="turtle")
    parsed = load_graph(turtle, format="turtle")
    iri = build_instance_iri(person, PrefixRegistry())
    with pytest.raises(OntoImportError, match="max_nesting_depth"):
        graph_to_instance(parsed, PersonMap, iri=iri, max_nesting_depth=0)


def test_router_auth_dependency_blocks_unauthenticated() -> None:
    from fastapi import Depends, Header, HTTPException, status

    async def require_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
        if x_api_key != "test-secret":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    client = TestClient(
        build_async_onto_test_app(
            entities=(Person,),
            router_kwargs={"dependencies": [Depends(require_key)]},
        )
    )
    with client:
        assert client.get("/onto/person/1").status_code == 422
        assert client.get("/onto/person/1", headers={"X-API-Key": "wrong"}).status_code == 401
        assert client.get("/onto/person/1", headers={"X-API-Key": "test-secret"}).status_code == 200
