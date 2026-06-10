"""Integration tests for OntoSession save/delete."""

from __future__ import annotations

import pytest

from ontosql import OntoSession
from tests.models import Organization, Person, PersonMap


@pytest.fixture
def writable_session(sync_engine):
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        yield session


from tests.models import OrganizationMap  # noqa: E402


def test_save_insert_and_get(writable_session) -> None:
    person = Person(id=50, name="New Person", employer=None)
    saved = writable_session.save(person)
    assert saved.id == 50
    loaded = writable_session.get(Person, id=50)
    assert loaded is not None
    assert loaded.name == "New Person"


def test_save_update_partial(writable_session) -> None:
    person = writable_session.get(Person, id=1)
    assert person is not None
    person.name = "Ada L."
    writable_session.save(person)
    reloaded = writable_session.get(Person, id=1)
    assert reloaded is not None
    assert reloaded.name == "Ada L."


def test_save_link_employer(writable_session) -> None:
    person = writable_session.get(Person, id=3)
    assert person is not None
    assert person.employer is None
    person.employer = Organization(id=10, name="Analytical Engines Inc.")
    writable_session.save(person)
    reloaded = writable_session.get(Person, id=3)
    assert reloaded is not None
    assert reloaded.employer is not None
    assert reloaded.employer.id == 10


def test_delete_person(writable_session) -> None:
    person = writable_session.get(Person, id=2)
    assert person is not None
    writable_session.delete(person)
    assert writable_session.get(Person, id=2) is None


def test_identity_map(writable_session) -> None:
    first = writable_session.get(Person, id=1)
    second = writable_session.get(Person, id=1)
    assert first is second


def test_flush_pending(writable_session) -> None:
    person = Person(id=60, name="Pending", employer=None)
    writable_session.save(person, flush=False)
    assert writable_session.get(Person, id=60) is None
    writable_session.flush()
    assert writable_session.get(Person, id=60) is not None


def test_rollback_pending(writable_session) -> None:
    person = Person(id=61, name="Rollback", employer=None)
    writable_session.save(person, flush=False)
    writable_session.rollback_pending()
    writable_session.flush()
    assert writable_session.get(Person, id=61) is None
