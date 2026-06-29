# Import API

Module: `ontosql.import_` (trailing underscore — `import` is a Python keyword).

## Errors

::: ontosql.import_.hydrate.OntoImportError

## Hydration

::: ontosql.import_.hydrate.graph_to_instance

::: ontosql.import_.hydrate.subject_iri_from_jsonld

## Parsing

::: ontosql.import_.parse.load_graph

::: ontosql.import_.parse.load_graph_from_jsonld

::: ontosql.import_.parse.find_subjects_by_type

## High-level import

::: ontosql.import_.import_from_rdf

::: ontosql.import_.import_from_jsonld

## Security

Set `untrusted=True` and byte/triple limits on public import paths — [SECURITY.md](../SECURITY.md).

## Related

- [HYBRID.md](../HYBRID.md) — RDF round-trip
