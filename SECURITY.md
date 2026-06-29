# Security

Security policy and threat model for OntoSQL.

**Full documentation:** [docs/SECURITY.md](docs/SECURITY.md)

## Reporting a vulnerability

Please report security issues privately via [GitHub Security Advisories](https://github.com/eddiethedean/ontosql/security/advisories/new) or by opening a confidential issue with the maintainers. Do not file public issues for undisclosed vulnerabilities.

## Quick reminders

- **`OntoRouter`** requires **`dependencies=[Depends(your_auth)]`** before any internet exposure — no built-in authn/authz.
- **`OntoRouter`** defaults: async sessions, `validate_entities=True`, `max_body_bytes=64 KiB`.
- **RDF import** — use `untrusted=True`; `max_triples` is checked after parse; authenticate import endpoints.
- **Graph sync** is eventual-consistency after SQL commit, not two-phase commit.
- **`CascadePolicy.REPLACE`** can delete nested rows — review [cascade policies](docs/guides/cascade-policies.md) before production use.
- **PyLD** compaction/framing on untrusted JSON-LD can trigger SSRF via remote `@context` fetches.
