# Support policy

OntoSQL **0.5.x is beta open-source software**. This page states what support exists today and what is planned for 1.0.

!!! info "Not a commercial product"
    OntoSQL has **no vendor support contract, SLA, or paid escalation path** in 0.5.x. Enterprise teams should plan internal ownership or wait for the 1.0 support policy described in [ROADMAP.md](ROADMAP.md).

## Current support (0.5.x)

| Channel | Use for |
|---------|---------|
| [GitHub Issues](https://github.com/eddiethedean/ontosql/issues) | Bugs, feature requests, questions |
| [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories) | Private vulnerability reports — see [SECURITY.md](SECURITY.md) |
| [Documentation](https://ontosql.readthedocs.io/) | Primary self-service (Read the Docs) |
| [FAQ](FAQ.md) / [Troubleshooting](TROUBLESHOOTING.md) | Common errors |

**Response expectations:** Best-effort by maintainers and contributors. No guaranteed response time.

## Version support

| Version | Status |
|---------|--------|
| **0.5.x** | Current beta; pin in production if you adopt |
| **&lt; 0.5** | Upgrade recommended; see [upgrading guide](guides/upgrading.md) |
| **1.0** (planned) | Semver guarantee, GA classifier, documented patch policy — [ROADMAP](ROADMAP.md) |

Pre-1.0 releases may add APIs in minor versions. Breaking changes are reserved for **2.0+** per roadmap; parameter renames may occur without deprecation until 1.0 — [SPECS](SPECS.md).

## Long-term support (LTS)

**Not defined until 1.0.** The roadmap plans:

- Which Python versions receive patches
- Which dependency major versions are supported
- Deprecation cycle (`DeprecationWarning` before removal)

Track [ROADMAP.md](ROADMAP.md) v0.9 (API freeze) and v1.0 (GA).

## Governance

| Topic | Current state |
|-------|----------------|
| **License** | MIT |
| **Maintainers** | Project contributors; see [GitHub repository](https://github.com/eddiethedean/ontosql) |
| **Decision process** | Maintainer-led; RFC process planned for 0.9 RC |
| **Corporate backing** | None documented |
| **Commercial support** | Not offered |

## Enterprise evaluation

Large organizations should read [enterprise adoption](enterprise-adoption.md) and complete the evaluation checklist before platform approval.

## Related

- [COMPATIBILITY.md](COMPATIBILITY.md) — Python and database matrix
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [Contributing](contributing.md) — how to contribute fixes and docs
