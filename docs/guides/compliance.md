# Compliance and security questionnaires

OntoSQL is **MIT-licensed open-source library software**, not a hosted service. This page helps security and compliance teams complete vendor questionnaires honestly.

!!! warning "Not certified"
    OntoSQL has **no SOC 2, ISO 27001, HIPAA BAA, FedRAMP, or PCI attestation**. Your application inherits compliance obligations for data storage, access control, and logging.

## What OntoSQL is responsible for

| Area | OntoSQL role |
|------|----------------|
| SQL compilation | Bound parameters for filter/save values; rejects raw `text()` in semantic filters — [SECURITY.md](../SECURITY.md) |
| HTTP scaffold | `OntoRouter` validates bodies and caps size; **does not** provide authn/authz |
| RDF import | Optional byte/triple/nesting limits; `untrusted=True` defaults |
| Graph sync | Post-commit queue; no two-phase commit |

## What your application is responsible for

| Area | Your responsibility |
|------|---------------------|
| **Authentication / authorization** | Required before public `OntoRouter` exposure |
| **Data at rest / in transit** | Database TLS, encryption, backups — OntoSQL uses your SQLAlchemy engine |
| **Audit logging** | Who accessed which `{entity_id}` — not built into OntoRouter |
| **PII / PHI handling** | Your semantic models and retention policies |
| **Network perimeter** | Rate limits, WAF, private networking |
| **Schema migrations** | Alembic and DBA processes — [Alembic guide](alembic.md) |
| **Supply chain** | Pin `ontosql` and transitive deps; scan your lockfile |

## Common framework mappings

These are **informative**, not certifications.

### SOC 2 (Trust Services Criteria)

| Criterion | OntoSQL contribution | Gap |
|-----------|---------------------|-----|
| CC6 Logical access | None — host app implements IAM | Full CC6 in your app + infra |
| CC7 System operations | Basic `ontosql` logger hooks | No SIEM integration; OTel planned 0.7 |
| CC8 Change management | Semver from 1.0 only | Pre-1.0 API may change — pin versions |

### HIPAA

OntoSQL is **not a Business Associate** by itself. If you process PHI:

- Run OntoSQL inside your HIPAA-compliant environment
- Do not expose `OntoRouter` without auth and audit trails
- Document mapper and export paths that serialize PHI to RDF/JSON-LD

### FedRAMP / government cloud

No FedRAMP authorization. Evaluate as **third-party open-source dependency** in your ATO package; include [SECURITY.md](../SECURITY.md) and dependency SBOM from your build.

### GDPR / data residency

OntoSQL does not store data. Residency is determined by **your SQL database and graph targets**. RDF export may duplicate personal data into graph stores — design retention and erasure in both SQL and graph layers.

## Data processing locations

| Component | Where data lives |
|-----------|------------------|
| `OntoSession` | Your configured SQL database |
| `StoreSyncTarget` / graph sync | In-process or SparqlModel store you configure |
| PyLD (`ontosql[jsonld]`) | May fetch remote `@context` URLs — SSRF risk on untrusted input |
| Read the Docs | Documentation only — not runtime |

## Vulnerability management

Report via [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories). **No published SLA** for fix or disclosure timelines in 0.5.x — see [SECURITY.md](../SECURITY.md#vulnerability-response).

## Third-party dependencies

Core: SQLModel, TripleModel (RDF), typing-extensions. Optional: FastAPI, PyLD, SparqlModel, pySHACL. See [DEPS.md](../DEPS.md) and [COMPATIBILITY.md](../COMPATIBILITY.md).

**SQL-only apps still install TripleModel** as a core dependency for CURIE expansion and optional export.

## Questionnaire quick answers

| Question | Answer |
|----------|--------|
| Is OntoSQL production-ready? | **No** — 0.5.x beta; GA at 1.0 |
| Is there commercial support? | **No** — community/GitHub only — [SUPPORT.md](../SUPPORT.md) |
| Where is data stored? | Your SQL DB and optional graph — not OntoSQL servers |
| Is multi-tenant isolation provided? | **No** — single-tenant library in your process |
| Penetration test available? | **No** published report |
| Performance SLA? | **None** — benchmarks planned 0.9 |

## Enterprise evaluation

Complete the [enterprise adoption checklist](../enterprise-adoption.md#evaluation-checklist) before procurement approval.

## Related

- [SECURITY.md](../SECURITY.md)
- [enterprise adoption](../enterprise-adoption.md)
- [SUPPORT.md](../SUPPORT.md)
