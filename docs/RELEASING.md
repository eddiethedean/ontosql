# Releasing SemSQL

Checklist for publishing a new version.

## Pre-release

1. Ensure `version` in `pyproject.toml` matches the release tag.
2. Update `CHANGELOG.md` (move items from `[Unreleased]` to a new version section).
3. Run the full CI suite locally:

   ```bash
   pip install -e ".[dev]"
   ruff check src tests
   ruff format --check src tests
   ty check
   pytest --cov=semsql --cov-fail-under=100
   ```

4. Build and smoke-test the wheel:

   ```bash
   pip install build
   python -m build
   pip install dist/semsql-*.whl
   python -c "import semsql; print(semsql.__version__)"
   ```

## GitHub release

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

Create a GitHub release from the tag and paste the relevant `CHANGELOG.md` section.

## PyPI (optional)

```bash
pip install twine
twine upload dist/*
```

Requires PyPI credentials configured (`~/.pypirc` or `TWINE_USERNAME` / `TWINE_PASSWORD`).
