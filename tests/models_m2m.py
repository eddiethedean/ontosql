"""Many-to-many fixtures for collection map tests."""

from __future__ import annotations

from sqlmodel import Field, SQLModel

from ontosql import Map, OntoMapper, OntoModel, onto_property
from ontosql.mapping.cascade import CascadePolicy


class M2MPersonRow(SQLModel, table=True):
    __tablename__ = "m2m_people"
    id: int | None = Field(default=None, primary_key=True)
    name: str


class SkillRow(SQLModel, table=True):
    __tablename__ = "skills"
    id: int | None = Field(default=None, primary_key=True)
    name: str


class PersonSkillRow(SQLModel, table=True):
    __tablename__ = "person_skills"
    person_id: int = Field(foreign_key="m2m_people.id", primary_key=True)
    skill_id: int = Field(foreign_key="skills.id", primary_key=True)


class Skill(OntoModel):
    type_iri = "schema:DefinedTerm"
    iri_template = "https://data.example.org/skill/{id}"

    id: int
    name: str = onto_property("schema:name")


class SkilledPerson(OntoModel):
    type_iri = "schema:Person"
    iri_template = "https://data.example.org/person/{id}"

    id: int
    name: str = onto_property("schema:name")
    skills: list[Skill] = onto_property("schema:knowsAbout", default_factory=list)


class SkillMap(OntoMapper[Skill]):
    entity = Skill
    id = Map(SkillRow.id)
    name = Map(SkillRow.name, property="schema:name")


class SkilledPersonMap(OntoMapper[SkilledPerson]):
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
        cascade=CascadePolicy.LINK,
    )
