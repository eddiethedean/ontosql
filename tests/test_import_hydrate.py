"""Unit tests for import hydrate helpers."""

from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode
from triplemodel import Store

from ontosql.import_.hydrate import (
    OntoImportError,
    _coerce_identity,
    _coerce_literal,
    _resolve_registry,
    _validate_type,
    subject_iri_from_jsonld,
)
from ontosql.registry import PrefixRegistry
from tests.models import Person, PersonMap


def test_resolve_registry_explicit() -> None:
    custom = PrefixRegistry({"ex": "https://example.org/"})
    reg = _resolve_registry(PersonMap, custom)
    assert reg is custom


def test_resolve_registry_default() -> None:
    reg = _resolve_registry(PersonMap, None)
    assert reg.expand("schema:name") == "https://schema.org/name"


def test_coerce_identity_from_iri() -> None:
    value = _coerce_identity(
        NamedNode("https://data.example.org/person/7"),
        Person,
        registry=PrefixRegistry(),
    )
    assert value == 7


def test_coerce_literal_int_float() -> None:
    reg = PrefixRegistry()
    assert _coerce_literal(Literal("42"), py_type=int, registry=reg, meta={}) == 42
    assert _coerce_literal(Literal("3.5"), py_type=float, registry=reg, meta={}) == 3.5
    assert _coerce_literal(Literal("false"), py_type=bool, registry=reg, meta={}) is False


def test_validate_type_missing_raises() -> None:
    graph = Store()
    subject = NamedNode("https://data.example.org/person/1")
    with pytest.raises(OntoImportError, match="rdf:type"):
        _validate_type(graph, subject, Person, PrefixRegistry())


def test_subject_iri_from_jsonld() -> None:
    assert subject_iri_from_jsonld({"@id": "https://example.org/x"}) == "https://example.org/x"


def test_subject_iri_from_jsonld_missing() -> None:
    with pytest.raises(OntoImportError):
        subject_iri_from_jsonld({})
