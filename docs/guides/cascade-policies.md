# Cascade policies

Nested fields use `Map.nested(..., cascade=...)` to define what happens on `save()`.

## Policies

| Policy | On save | Use when |
|--------|---------|----------|
| **`link`** (default) | Updates parent FK only; nested row must already exist | Shared reference data (many people → same org) |
| **`upsert`** | Insert or update nested row; set parent FK | Owned nested data, shared updates OK |
| **`replace`** | Delete old nested row when association changes; then upsert new | Sole ownership of nested row |
| **`ignore`** | Skip nested persistence | Read-only or externally managed nested |

Always set `fk_column=` when cascade is not `ignore`.

## Example: link (default)

```python
employer = Map.nested(
    Organization,
    join=PersonRow.org_id == OrgRow.id,
    nested_map=OrganizationMap,
    property="schema:worksFor",
    fk_column=PersonRow.org_id,
    cascade=CascadePolicy.LINK,
)
```

Saving a `Person` with `employer=Organization(id=10, ...)` sets `people.org_id = 10`. The org row must exist.

## Example: replace

```python
employer = Map.nested(
    Organization,
    ...,
    cascade=CascadePolicy.REPLACE,
    fk_column=PersonRow.org_id,
)
```

When the employer changes from org `10` to org `20`, OntoSQL deletes org `10` **only if** no other parent row still references it. Otherwise `ExecuteError` is raised.

**Do not use `REPLACE` for nested rows shared across multiple parents** — use `LINK` or `IGNORE`.

## Execution order (replace)

On REPLACE with FK change:

1. Parent FK is nulled
2. Old nested row is deleted (if exclusively owned)
3. New nested row is upserted
4. Parent FK is updated

## Related

- [SPECS.md](../SPECS.md#cascade-policies-write-path-030)
- [HYBRID.md](../HYBRID.md#cascadepolicyreplace)
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
