# Bridge tables (many-to-many)

Use `Map.collection` when a semantic list field is backed by a **bridge table** joining two entity tables.

## Schema

```text
people ──< person_skills >── skills
```

```python
class PersonSkillRow(SQLModel, table=True):
    __tablename__ = "person_skills"
    person_id: int = Field(foreign_key="people.id", primary_key=True)
    skill_id: int = Field(foreign_key="skills.id", primary_key=True)
```

## Semantic model

```python
class Person(OntoModel):
  ...
  skills: list[Skill] = onto_property("schema:knowsAbout")
```

## Mapper

```python
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
```

## Read path

Collections are **not** joined into the root `SELECT` (avoids row explosion). After `find` / `get`, OntoSQL runs **one batched query per collection field** for all root identities in the result set.

## Write cascade policies

| Policy | Behavior |
|--------|----------|
| `link` (default) | Replace bridge links for the parent; nested entities must already exist |
| `upsert` | Upsert each nested entity, then replace bridge links |
| `replace` | Same bridge sync as `upsert` (diff via replace-all bridge rows for parent) |
| `ignore` | Do not persist collection changes |

On save, bridge rows for the parent are cleared and re-inserted for the new link set.

## When to use nested vs collection

| Pattern | Binding |
|---------|---------|
| One parent → one child via FK | `Map.nested` |
| Many parents ↔ many children | `Map.collection` |

## Anti-patterns

- **Shared taxonomy nodes** (e.g. global skill vocabulary) — use `link` so saves only touch bridge rows.
- **Owned child rows** exclusive to one parent — consider `Map.nested` with a FK instead.

## Related

- [Cascade policies](cascade-policies.md)
- [Multi-map views](multi-map-views.md)
