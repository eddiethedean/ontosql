# Security

Security policy and threat model for OntoSQL.

**Full documentation:** [docs/SECURITY.md](docs/SECURITY.md)

## Reporting a vulnerability

Please report security issues privately via [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories/new) or by opening a confidential issue with the maintainers. Do not file public issues for undisclosed vulnerabilities.

## Quick reminders

- **`OntoRouter`** is demo-grade — no authn, authz, or rate limits.
- **`execute_sql()`** is an escape hatch — use bound parameters, never concatenate user input.
- **Graph sync** is eventual-consistency after SQL commit, not two-phase commit.
- **`CascadePolicy.REPLACE`** can delete nested rows — review [cascade policies](docs/guides/cascade-policies.md) before production use.
