"""Integration tests for OntoSession save/delete."""

from __future__ import annotations

import pytest

from ontosql import Map, OntoMapper, OntoSession
from ontosql.compile.write import WriteCompileError
from ontosql.mapping.cascade import CascadePolicy
from tests.models import Organization, OrganizationMap, OrgRow, Person, PersonMap, PersonRow


@pytest.fixture
def writable_session(sync_engine):
    with OntoSession(sync_engine, maps=[PersonMap, OrganizationMap]) as session:
        yield session


@pytest.fixture
def upsert_person_map():
    class UpsertPersonMap(OntoMapper[Person]):
        entity = Person
        id = Map(PersonRow.id)
        name = Map(PersonRow.name, property="schema:name")
        employer = Map.nested(
            Organization,
            join=PersonRow.org_id == OrgRow.id,
            nested_map=OrganizationMap,
            property="schema:worksFor",
            fk_column=PersonRow.org_id,
            cascade=CascadePolicy.UPSERT,
        )

    return UpsertPersonMap


def test_save_insert_and_get(writable_session) -> None:
    person = Person(id=50, name="New Person", employer=None)
    saved = writable_session.save(person)
    assert saved.id == 50
    loaded = writable_session.get(Person, id=50)
    assert loaded is not None
    assert loaded.name == "New Person"


def test_save_reload_after_autoincrement_insert(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        person = Person.model_construct(name="Auto ID", id=None)
        saved = session.save(person)
        assert saved.id is not None
        assert saved.name == "Auto ID"
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        loaded = session.get(Person, id=saved.id)
        assert loaded is not None
        assert loaded.name == "Auto ID"


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


def test_save_link_requires_nested_identity(writable_session) -> None:
    person = writable_session.get(Person, id=3)
    assert person is not None
    person.employer = Organization.model_construct(id=None, name="Unsaved Org")
    with pytest.raises(WriteCompileError, match="identity"):
        writable_session.save(person)


def test_save_upserts_existing_nested_org(sync_engine, upsert_person_map) -> None:
    with OntoSession(sync_engine, maps=[upsert_person_map, OrganizationMap]) as session:
        person = session.get(Person, id=1)
        assert person is not None
        assert person.employer is not None
        person.employer = Organization(id=10, name="Renamed Org")
        session.save(person)
        reloaded = session.get(Person, id=1)
        assert reloaded is not None
        assert reloaded.employer is not None
        assert reloaded.employer.name == "Renamed Org"


def test_save_upsert_inserts_new_nested_org(sync_engine, upsert_person_map) -> None:
    with OntoSession(sync_engine, maps=[upsert_person_map, OrganizationMap]) as session:
        person = session.get(Person, id=3)
        assert person is not None
        assert person.employer is None
        person.employer = Organization.model_construct(id=None, name="New Upsert Org")
        session.save(person)
        reloaded = session.get(Person, id=3)
        assert reloaded is not None
        assert reloaded.employer is not None
        assert reloaded.employer.id is not None
        assert reloaded.employer.name == "New Upsert Org"


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


def test_sync_rollback_discards_uncommitted_write(sync_engine) -> None:
    with (
        pytest.raises(RuntimeError, match="abort"),
        OntoSession(sync_engine, maps=[PersonMap]) as session,
    ):
        session.save(Person(id=500, name="Should Not Persist", employer=None))
        raise RuntimeError("abort")
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        assert session.get(Person, id=500) is None


def test_count_with_filter(writable_session) -> None:
    total = writable_session.count(Person)
    assert total == 3
    filtered = writable_session.count(Person, where=Person.name.startswith("A"))
    assert filtered == 1
