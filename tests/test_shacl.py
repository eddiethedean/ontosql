"""Tests for SHACL generation and validation."""

from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from ontosql.export.instance import instance_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.shacl import shapes_from_mapper, shapes_from_mappers, validate_instance
from tests.models import Organization, OrganizationMap, Person, PersonMap

SH = "http://www.w3.org/ns/shacl#"


def test_shapes_from_mapper() -> None:
    shapes = shapes_from_mapper(PersonMap)
    reg = PrefixRegistry()
    name_shape = NamedNode(f"{reg.expand('schema:Person')}Shape/name")
    paths = [str(node.value) for node in shapes.objects(name_shape, NamedNode(f"{SH}path"))]
    assert paths == [reg.expand("schema:name")]
    min_counts = shapes.objects(name_shape, NamedNode(f"{SH}minCount"))
    assert any(str(getattr(lit, "value", lit)) == "1" for lit in min_counts)
    employer_shape = NamedNode(f"{reg.expand('schema:Person')}Shape/employer")
    employer_min = shapes.objects(employer_shape, NamedNode(f"{SH}minCount"))
    assert any(str(getattr(lit, "value", lit)) == "0" for lit in employer_min)


def test_shapes_required_scalar_min_count_regression() -> None:
    """Regression: required scalars with ontology predicates must get minCount 1."""
    shapes = shapes_from_mapper(PersonMap)
    reg = PrefixRegistry()
    prop = NamedNode(f"{reg.expand('schema:Person')}Shape/name")
    mins = [
        str(getattr(lit, "value", lit))
        for lit in shapes.objects(prop, NamedNode(f"{SH}minCount"))
    ]
    assert mins == ["1"]


def test_shapes_from_mappers_includes_nested() -> None:
    shapes = shapes_from_mappers([PersonMap, OrganizationMap])
    reg = PrefixRegistry()
    org_shape = NamedNode(f"{reg.expand('schema:Organization')}Shape")
    assert any(str(triple[0]) == str(org_shape) for triple in shapes)


def test_validate_instance() -> None:
    pytest.importorskip("pyshacl")
    person = Person(
        id=1,
        name="Ada Lovelace",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    report = validate_instance(person, PersonMap)
    assert report.conforms is True


def test_validate_instance_invalid() -> None:
    pyshacl = pytest.importorskip("pyshacl")
    reg = PrefixRegistry()
    person = Person(id=1, name="Ada", employer=None)
    data = instance_to_graph(person)
    subject = NamedNode("https://data.example.org/person/1")
    name_pred = NamedNode(reg.expand("schema:name"))
    for obj in list(data.objects(subject, name_pred)):
        data.remove((subject, name_pred, obj))

    shapes = shapes_from_mapper(PersonMap)
    conforms, _, _ = pyshacl.validate(
        data.serialize(format="turtle"),
        shacl_graph=shapes.serialize(format="turtle"),
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False,
    )
    assert conforms is False
