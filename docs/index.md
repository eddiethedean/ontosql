# OntoSQL

**Semantic data access for SQL** — a Python mapper (SQLModel + Pydantic) with optional RDF export. **Not** a SPARQL database or OBDA query engine.

> **Who is this for?** Teams building **SQL-first** apps (Postgres, SQLite) that want **ontology-shaped Python models** and optional JSON-LD/RDF APIs. RDF and graph sync are optional.

Real databases are not one table per ontology class. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with an explicit **mapper**. Application code uses semantic types; OntoSQL compiles SQL on the backend.

## Start here

1. [Installation](getting-started/installation.md)
2. [Quick start](getting-started/quickstart.md) — runnable from PyPI in under 10 minutes (no clone)
3. [Architecture](ARCHITECTURE.md) — why two model layers and explicit maps
4. [Ecosystem](ECOSYSTEM.md) — OntoSQL vs SQLModel vs SparqlModel
5. [Hybrid deployments](HYBRID.md) — SQL + RDF graph sync (optional)
6. [Technical specification](SPECS.md) — full API reference

## Install

```bash
pip install ontosql
pip install "ontosql[async]"     # AsyncOntoSession + SQLite
pip install "ontosql[fastapi]"   # OntoRouter + content negotiation
pip install "ontosql[jsonld]"    # optional JSON-LD compact/frame (PyLD)
pip install "ontosql[sparql]"    # SparqlModel graph sync adapter
pip install "ontosql[shacl]"     # SHACL shape generation + validation
```

**Requirements:** Python 3.10+. See [Compatibility](COMPATIBILITY.md).

**Examples:** The `examples/` scripts require a [repository clone](https://github.com/eddiethedean/ontosql) — they are not shipped in the PyPI wheel. Use the [quick start](getting-started/quickstart.md) for a pip-only path.
