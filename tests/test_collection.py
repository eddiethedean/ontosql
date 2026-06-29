"""Tests for Map.collection (many-to-many bridge tables)."""

from __future__ import annotations

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from ontosql import AsyncOntoSession, OntoSession
from ontosql.mapping.cascade import CascadePolicy
from tests.models_m2m import (
    M2MPersonRow,
    PersonSkillRow,
    Skill,
    SkilledPerson,
    SkilledPersonMap,
    SkillMap,
    SkillRow,
)


@pytest.fixture
def m2m_engine():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(M2MPersonRow(id=1, name="Ada"))
        session.add(M2MPersonRow(id=2, name="Grace"))
        session.add(SkillRow(id=10, name="SQL"))
        session.add(SkillRow(id=11, name="RDF"))
        session.add(PersonSkillRow(person_id=1, skill_id=10))
        session.add(PersonSkillRow(person_id=1, skill_id=11))
        session.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def m2m_session(m2m_engine):
    with OntoSession(m2m_engine, maps=[SkilledPersonMap, SkillMap]) as session:
        yield session


def test_collection_find_loads_skills(m2m_session) -> None:
    person = m2m_session.get(SkilledPerson, identity=1)
    assert person is not None
    assert len(person.skills) == 2
    names = {s.name for s in person.skills}
    assert names == {"SQL", "RDF"}


def test_collection_find_empty(m2m_session) -> None:
    person = m2m_session.get(SkilledPerson, identity=2)
    assert person is not None
    assert person.skills == []


def test_collection_batched_queries(m2m_engine) -> None:
    query_count = 0

    @event.listens_for(m2m_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    with OntoSession(m2m_engine, maps=[SkilledPersonMap, SkillMap]) as session:
        people = session.find(SkilledPerson)
        assert len(people) == 2
        assert len(people[0].skills) == 2
    # one root SELECT + one collection SELECT (not N+1 per person)
    assert query_count == 2


def test_collection_save_link(m2m_session) -> None:
    person = m2m_session.get(SkilledPerson, identity=2)
    assert person is not None
    person.skills = [Skill(id=10, name="SQL")]
    m2m_session.save(person)
    reloaded = m2m_session.get(SkilledPerson, identity=2)
    assert reloaded is not None
    assert len(reloaded.skills) == 1
    assert reloaded.skills[0].name == "SQL"


def test_collection_save_upsert(m2m_engine) -> None:
    from ontosql import Map, OntoMapper

    class UpsertSkilledPersonMap(OntoMapper[SkilledPerson]):
        entity = SkilledPerson
        id = Map(M2MPersonRow.id)
        name = Map(M2MPersonRow.name, property="schema:name")
        skills = Map.collection(
            Skill,
            through=PersonSkillRow,
            source_fk=PersonSkillRow.person_id,
            target_fk=PersonSkillRow.skill_id,
            nested_map=SkillMap,
            field="skills",
            property="schema:knowsAbout",
            cascade=CascadePolicy.UPSERT,
        )

    from ontosql import OntoSession

    with OntoSession(m2m_engine, maps=[UpsertSkilledPersonMap, SkillMap]) as session:
        person = session.get(SkilledPerson, identity=2)
        assert person is not None
        person.skills = [Skill.model_construct(name="Python", id=None)]
        session.save(person)
        reloaded = session.get(SkilledPerson, identity=2)
        assert reloaded is not None
        assert len(reloaded.skills) == 1
        assert reloaded.skills[0].name == "Python"


@pytest.mark.asyncio
async def test_collection_async_find(m2m_engine) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    async_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    from sqlalchemy.ext.asyncio import AsyncSession

    async with AsyncSession(async_engine) as raw:
        raw.add(M2MPersonRow(id=1, name="Ada"))
        raw.add(SkillRow(id=10, name="SQL"))
        raw.add(PersonSkillRow(person_id=1, skill_id=10))
        await raw.commit()

    async with AsyncOntoSession(async_engine, maps=[SkilledPersonMap, SkillMap]) as session:
        person = await session.get(SkilledPerson, identity=1)
        assert person is not None
        assert len(person.skills) == 1
    await async_engine.dispose()
