# Releasing OntoSQL

Checklist for publishing a new version.

## Pre-release

1. Ensure `version` in `pyproject.toml` matches the release tag.
2. Update `CHANGELOG.md` (move items from `[Unreleased]` to a new version section).
3. Confirm README, [SPECS.md](SPECS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ECOSYSTEM.md](ECOSYSTEM.md), and [CHANGELOG](changelog.md) are aligned with the release scope.
4. Run the full CI suite locally:

   ```bash
   pip install -e ".[dev]"
   ruff check src tests
   ruff format --check src tests
   ty check
   pytest --cov=ontosql --cov-fail-under=90
   mkdocs build --strict
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
git tag -a vX.Y.Z -m "Release X.Y.Z"
git push origin vX.Y.Z
```

Create a GitHub release from the tag and paste the relevant `CHANGELOG.md` section.

Pushing a semver tag (`v*.*.*`) also triggers the [Release workflow](https://github.com/eddiethedean/ontosql/blob/main/.github/workflows/release.yml) to build and publish to PyPI.

## PyPI

The PyPI distribution name is **`ontosql`**.

### Automated publish (recommended)

1. Create a PyPI API token at [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/) scoped to the **`ontosql`** project (or the whole account for the first upload).
2. Add it as a GitHub repository secret named **`PYPI_API_TOKEN`** (`Settings` → `Secrets and variables` → `Actions`).
3. Tag and push — the [Release workflow](https://github.com/eddiethedean/ontosql/blob/main/.github/workflows/release.yml) runs on tags matching `v*.*.*`:

   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

### Manual publish

```bash
python -m build
pip install twine
twine check dist/*
twine upload dist/*
```

Requires PyPI credentials configured (`~/.pypirc` or `TWINE_USERNAME=__token__` / `TWINE_PASSWORD`).

PyPI `description` and `readme` come from [pyproject.toml](https://github.com/eddiethedean/ontosql/blob/main/pyproject.toml) — update them in the same release PR as [README.md](https://github.com/eddiethedean/ontosql/blob/main/README.md).

## Documentation hosting

Docs are built with MkDocs (`mkdocs build --strict`) from [mkdocs.yml](https://github.com/eddiethedean/ontosql/blob/main/mkdocs.yml).

| Host | Role | Trigger |
|------|------|---------|
| **[Read the Docs](https://ontosql.readthedocs.io/)** | **Canonical** public documentation | RTD webhook on push/tags — [`.readthedocs.yaml`](https://github.com/eddiethedean/ontosql/blob/main/.readthedocs.yaml) |
| **GitHub Pages** | Optional mirror | Push to `main` — [pages workflow](https://github.com/eddiethedean/ontosql/blob/main/.github/workflows/pages.yml) |

Use **Read the Docs** URLs in README, PyPI `Documentation` field, and external links. GitHub Pages is a convenience mirror only.

**One-time RTD setup:** create a project named `ontosql`, point at this repository, enable builds for `main` and tags. `.readthedocs.yaml` installs `pip install ".[docs]"` and runs MkDocs with `fail_on_warning: true`.
