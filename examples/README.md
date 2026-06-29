# OntoSQL examples

Runnable scripts demonstrating sync CRUD, async sessions, hybrid graph sync, and production FastAPI patterns.

**Not included in the PyPI wheel** — clone the repository:

```bash
git clone https://github.com/eddiethedean/ontosql.git
cd ontosql
pip install -e ".[dev]"
```

## Layout

| File | What it teaches |
|------|-----------------|
| [person_org_demo.py](person_org_demo.py) | Sync CRUD round-trip (`get`, `save`, `delete`, semantic queries) |
| [person_org_async.py](person_org_async.py) | `AsyncOntoSession` parity |
| [hybrid_person_org.py](hybrid_person_org.py) | Graph sync on commit, RDF import |
| [person_org_api_production.py](person_org_api_production.py) | Production FastAPI with auth and lifespan |
| [models.py](models.py) | Shared Person/Organization row models, semantic models, and mappers |
| [_bootstrap.py](_bootstrap.py) | Adds `examples/` to `sys.path` so scripts can `import models` |

## Running

From the repository root:

```bash
python examples/person_org_demo.py
python examples/person_org_async.py
python examples/hybrid_person_org.py
python examples/person_org_api_production.py
```

Each script imports `_bootstrap` first (see top of `person_org_demo.py`). Do **not** import `tests.models` from examples — tests use a separate fixture module.

## Pip-only alternative

For a self-contained walkthrough without cloning, use the [quick start](../docs/getting-started/quickstart.md) or [tutorial](../docs/getting-started/tutorial.md).
