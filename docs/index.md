# OntoSQL

!!! warning "0.5.x beta"
    API stability tiers are documented in [SPECS](SPECS.md). Semver guarantees begin at 1.0.
    Pin versions in production and read [Compatibility](COMPATIBILITY.md) before upgrading.

<div class="os-hero" markdown="0">
  <div class="os-hero-badges">
    <span class="os-badge os-badge--accent">0.5.x</span>
    <span class="os-badge">Python 3.10+</span>
    <span class="os-badge">SQLModel + Pydantic</span>
    <span class="os-badge">JSON-LD · RDF optional</span>
  </div>
  <p class="os-hero-kicker">OntoSQL documentation</p>
  <p class="os-hero-title">Semantic data access for SQL-first Python apps</p>
  <p class="os-lead">Map ontology-shaped Pydantic models onto real SQL schemas with explicit mappers. Get CRUD, semantic queries, and optional JSON-LD/RDF export from one source of truth — not a SPARQL database.</p>
  <div class="os-hero-actions">
    <a class="os-hero-cta" href="getting-started/quickstart/">Quick start →</a>
    <a class="os-hero-cta os-hero-cta--secondary" href="guides/start-here/">Choose your path</a>
  </div>
</div>

Pick the path that matches how you work:

<div class="grid cards" markdown="1">

-   :material-database:{ .lg .middle } **SQL CRUD**

    ---

    Semantic models, explicit maps, and `OntoSession` — no RDF required. Runnable from PyPI in minutes.

    [:octicons-arrow-right-24: Quick start](getting-started/quickstart.md)

-   :material-api:{ .lg .middle } **FastAPI API**

    ---

    `OntoRouter`, content negotiation, async lifespan, and production security patterns.

    [:octicons-arrow-right-24: FastAPI quick start](guides/fastapi-quickstart.md)

-   :material-graph-outline:{ .lg .middle } **Hybrid SQL + graph**

    ---

    Mirror SQL writes to RDF on commit; import JSON-LD; materialize graph views.

    [:octicons-arrow-right-24: Hybrid guide](HYBRID.md)

-   :material-help-circle:{ .lg .middle } **Not sure?**

    ---

    Start here for a single next step based on your goal.

    [:octicons-arrow-right-24: Start here](guides/start-here.md)

</div>

!!! tip "Who is this for?"

    Teams building **SQL-first** apps (Postgres, SQLite) that want **ontology-shaped Python models** and optional JSON-LD/RDF APIs. RDF and graph sync are optional.

<div class="os-callout" markdown="0">
  <strong>Production note:</strong> <code>OntoRouter</code> requires <code>dependencies=[Depends(your_auth)]</code> before internet exposure. Graph sync is <strong>eventually consistent</strong> after SQL commit. See <a href="SECURITY/">Security</a>.
</div>

## What you need

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10+ — see [Compatibility](COMPATIBILITY.md) |
| **Install** | `pip install ontosql` — extras for async, FastAPI, JSON-LD, SparqlModel, SHACL |
| **Examples** | Repo clone for `examples/` scripts; [quick start](getting-started/quickstart.md) works from PyPI only |

```bash
pip install ontosql
pip install "ontosql[async]"     # AsyncOntoSession
pip install "ontosql[fastapi]"   # OntoRouter
pip install "ontosql[jsonld]"    # JSON-LD compact/frame
pip install "ontosql[sparql]"     # SparqlModel graph sync
pip install "ontosql[shacl]"      # SHACL shapes
```

Release notes: [changelog](changelog.md) · [GitHub CHANGELOG](https://github.com/eddiethedean/ontosql/blob/main/CHANGELOG.md)

## Read next

New to OntoSQL? Follow [Start here](guides/start-here.md), the [quick start](getting-started/quickstart.md), or the [tutorial](getting-started/tutorial.md).

Evaluating adoption? Read [When to use OntoSQL](getting-started/when-to-use.md), [Enterprise adoption](enterprise-adoption.md), and [Security](SECURITY.md).

Questions? See [FAQ](FAQ.md) or [Troubleshooting](TROUBLESHOOTING.md).
