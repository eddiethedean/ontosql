# Contributing to OntoSQL

Thank you for contributing. This project is in active development (**0.5.x beta**). Semver guarantees begin at 1.0 — see [ROADMAP.md](ROADMAP.md).

Please read the [Code of Conduct](code_of_conduct.md).

## Setup

```bash
git clone https://github.com/eddiethedean/ontosql.git
cd ontosql
pip install -e ".[dev]"
```

## Run checks (same as CI)

```bash
ruff check src tests
ruff format --check src tests
ty check
pytest --cov=ontosql --cov-fail-under=90
mkdocs build --strict
```

Install docs tooling with `pip install -e ".[docs]"` (also included in `.[dev]`).

### Run a subset of tests

During development you do not need the full suite every time:

```bash
pytest tests/test_session_write_sync.py -q          # sync CRUD
pytest tests/test_session_async.py -q               # async parity
pytest tests/test_mapping.py -q                     # mapper validation
```

Postgres integration tests require `ONTO_TEST_DATABASE_URL` (see CI postgres job).

## Project layout

```text
src/ontosql/     # library code
tests/           # pytest suite; shared fixtures in tests/models.py
examples/        # runnable demos; shared fixtures in examples/models.py
docs/            # documentation (MkDocs site)
```

- **Tests** use `tests/models.py` for Person/Organization fixtures.
- **Examples** use `examples/models.py` — do not import `tests.models` from examples.

## Pull requests

1. Branch from `main`
2. Add or update tests for behavior changes
3. Update docs and `CHANGELOG.md` `[Unreleased]` when user-facing behavior changes
4. Ensure CI passes locally before opening PR

Use the PR template checklist (tests, changelog, docs).

## Code style

- Ruff for lint and format (line length 100)
- `ty check` on `src/ontosql`
- Match existing patterns; avoid drive-by refactors

## Issue labels

Maintainers use these labels:

| Label | Use |
|-------|-----|
| `good first issue` | Small, isolated tasks — docs, examples, typo fixes |
| `documentation` | README, guides, MkDocs |
| `bug` | Incorrect behavior |
| `enhancement` | New features |

Label definitions: [`.github/labels.yml`](https://github.com/eddiethedean/ontosql/blob/main/.github/labels.yml) on GitHub.

## Releases

Maintainers: see [RELEASING.md](RELEASING.md).

## Questions

Open a [GitHub issue](https://github.com/eddiethedean/ontosql/issues) for bugs and feature requests.
