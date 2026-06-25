# Contributing to OntoSQL

Thank you for contributing. This project is in active development (0.4.x beta).

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

## Project layout

```text
src/ontosql/     # library code
tests/           # pytest suite; shared fixtures in tests/models.py
examples/        # runnable demos; shared fixtures in examples/models.py
docs/            # documentation
```

- **Tests** use `tests/models.py` for Person/Organization fixtures.
- **Examples** use `examples/models.py` — do not import `tests.models` from examples.

## Pull requests

1. Branch from `main`
2. Add or update tests for behavior changes
3. Update docs and `CHANGELOG.md` `[Unreleased]` when user-facing behavior changes
4. Ensure CI passes locally before opening PR

## Code style

- Ruff for lint and format (line length 100)
- `ty check` on `src/ontosql`
- Match existing patterns; avoid drive-by refactors

## Releases

Maintainers: see [docs/RELEASING.md](https://github.com/eddiethedean/ontosql/blob/main/docs/RELEASING.md).

## Questions

Open a [GitHub issue](https://github.com/eddiethedean/ontosql/issues) for bugs and feature requests.
