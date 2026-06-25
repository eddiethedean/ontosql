# OntoSQL

**Semantic data access for SQL** — map ontology-shaped models onto real database schemas and write CRUD in Python, not RDF.

Real databases are not one table per ontology class. OntoSQL separates **physical** SQLModel tables from **semantic** Pydantic entities and connects them with an explicit **mapper**. Application code uses semantic types; OntoSQL compiles SQL on the backend.

## Start here

1. [Installation](getting-started/installation.md)
2. [Quick start](getting-started/quickstart.md) — runnable in under 10 minutes from PyPI
3. [Architecture](ARCHITECTURE.md) — why two model layers and explicit maps
4. [Hybrid deployments](HYBRID.md) — SQL + RDF graph sync (optional)
5. [Technical specification](SPECS.md) — full API reference

## Install

```bash
pip install ontosql
pip install "ontosql[fastapi]"   # OntoRouter + content negotiation
pip install "ontosql[jsonld]"    # optional JSON-LD compact/frame (PyLD)
pip install "ontosql[sparql]"    # SparqlModel graph sync adapter
pip install "ontosql[shacl]"     # SHACL shape generation + validation
```

**Requirements:** Python 3.10+. See [Compatibility](COMPATIBILITY.md).
