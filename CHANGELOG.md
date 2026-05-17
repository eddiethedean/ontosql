# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-16

First public release.

### Added

- `onto_field()` — SQLModel field helper with ontology metadata in `json_schema_extra`
- `onto_model()` / `apply_onto_model()` — class decorator for RDF `@type` and instance IRI templates
- `OntoMixin` — `to_jsonld()`, `to_rdf()`, and `onto_context()` on model instances
- `PrefixRegistry` — CURIE expansion, compaction, and JSON-LD `@context` building
- JSON-LD export with `@context`, `@id`, `@type`, nested objects, and FK `@id` references
- RDF export via RDFLib (Turtle, JSON-LD, N-Triples, RDF/XML)
- JSON-safe literal coercion for `datetime`, `date`, `UUID`, `Decimal`, `Enum`, and `tuple`
- Optional `semsql[fastapi]` extra: response classes and `negotiate_onto_response()` with `Accept` header negotiation
- Example FastAPI app in `examples/fastapi_demo.py`
- Documentation: `SPECS.md`, `PLAN.md`, `DEPS.md`, `ROADMAP.md`

### Fixed

- FastAPI `Accept` parsing now handles `charset`, `q` weights, and rejects `q=0` correctly
- Duplicate ontology property keys prefer nested objects over foreign-key integers (with warning)
- `orjson` used for JSON-LD responses when installed via the `fastapi` extra

[0.1.0]: https://github.com/eddiethedean/semsql/releases/tag/v0.1.0
