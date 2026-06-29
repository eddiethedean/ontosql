# Export API

RDF export from semantic instances. Uses [TripleModel](https://github.com/eddiethedean/triplemodel) internally.

## Instance export

::: ontosql.export.instance.instance_to_graph

::: ontosql.export.instance.instance_to_jsonld

::: ontosql.export.instance.instance_to_rdf

::: ontosql.export.instance.write_instance_to_graph

## Batch export

::: ontosql.export.instance.instances_to_graph

::: ontosql.export.instance.instances_to_jsonld

::: ontosql.export.instance.instances_to_rdf

## Instance methods

`OntoModel.to_jsonld()` and `OntoModel.to_rdf()` delegate to these helpers — see [SPECS.md](../SPECS.md).

## Related

- [HYBRID.md](../HYBRID.md) — materialized views
- [when-to-use.md](../getting-started/when-to-use.md) — RDF optional for SQL-only apps
