# Semantic queries

`OntoSession.find()` and `count()` accept **semantic field expressions**. OntoSQL compiles joins from your `OntoMapper` — you do not write SQL for nested filters.

## Basics

```python
# Equality and comparisons
session.find(Person, where=Person.name == "Ada Lovelace")
session.find(Person, where=Person.id > 10)

# String filters
session.find(Person, where=Person.name.startswith("A"))
session.find(Person, where=Person.name.contains("Lovelace"))
session.find(Person, where=Person.name.endswith("ace"))

# Membership and null
session.find(Person, where=Person.id.in_([1, 2, 3]))
session.find(Person, where=Person.employer.is_null())
```

## Nested paths

Filter on joined semantic fields via `FieldPath`:

```python
session.find(
    Person,
    where=Person.employer.name.startswith("Analytical"),
)
```

OntoSQL adds the join from `Map.nested` on `PersonMap.employer`.

## Boolean combinations

```python
session.find(
    Person,
    where=(Person.name.startswith("A")) & (Person.id > 0),
)
session.find(
    Person,
    where=(Person.name == "Ada") | (Person.name == "Grace"),
)
```

## Ordering and pagination

```python
from ontosql.query import OrderBy

session.find(
    Person,
    where=Person.name.startswith("A"),
    order_by=OrderBy(Person.name, desc=True),
    limit=20,
    offset=0,
)

from ontosql import paginate

page = paginate(session, Person, where=Person.id > 0, limit=10, offset=0)
print(page.items, page.total)
```

## Count

```python
n = session.count(Person, where=Person.employer.name.contains("Engine"))
```

## What is not supported

- Raw `sqlalchemy.text()` in `where` — rejected at compile time ([SECURITY](../SECURITY.md))
- Arbitrary SQL strings — use SQLAlchemy session directly for ad hoc SQL
- Aggregations (`GROUP BY`, `SUM`) — planned for 0.6 ([ROADMAP](../ROADMAP.md))

Unsupported expressions raise at **compile time**, not at runtime.

## Async

Same API with `await`:

```python
people = await session.find(Person, where=Person.name.startswith("A"))
page = await paginate_async(session, Person, limit=10)
```

## Related

- [SPECS.md](../SPECS.md#query-expressions) — operator list
- [API reference](../reference/session.md) — `find`, `count`, `paginate`
- [Postgres dialect](postgres-dialect.md) — UUID, JSONB filters
