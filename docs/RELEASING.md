# Releasing OntoSQL

Checklist for publishing a new version.

## Pre-release

1. Ensure `version` in `pyproject.toml` matches the release tag.
2. Update `CHANGELOG.md` (move items from `[Unreleased]` to a new version section).
3. Confirm README, [SPECS.md](SPECS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ECOSYSTEM.md](ECOSYSTEM.md), and CHANGELOG are aligned with the release scope.
4. Run the full CI suite locally:

   ```bash
   pip install -e ".[dev]"
   ruff check src tests
   ruff format --check src tests
   ty check
   pytest --cov=ontosql --cov-fail-under=100
   ```

5. Build and smoke-test the wheel:

   ```bash
   pip install build
   python -m build
   pip install dist/ontosql-*.whl
   python -c "import ontosql; print(ontosql.__version__)"
   ```

## GitHub release

```bash
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0
```

Create a GitHub release from the tag and paste the relevant `CHANGELOG.md` section.

## PyPI

The PyPI distribution name is **`ontosql`**.

```bash
python -m build
pip install twine
twine check dist/*
twine upload dist/*
```

Requires PyPI credentials configured (`~/.pypirc` or `TWINE_USERNAME` / `TWINE_PASSWORD`).

PyPI `description` and `readme` come from [pyproject.toml](../pyproject.toml) — update them in the same release PR as [README.md](../README.md).
