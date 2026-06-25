"""Tests for SHACL generation and validation."""

from __future__ import annotations

import pytest

from ontosql.shacl import shapes_from_mapper, validate_instance
from tests.models import Organization, Person, PersonMap


def test_shapes_from_mapper() -> None:
    shapes = shapes_from_mapper(PersonMap)
    assert len(shapes) > 0


def test_validate_instance() -> None:
    pyshacl = pytest.importorskip("pyshacl")
    _ = pyshacl
    person = Person(
        id=1,
        name="Ada Lovelace",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    report = validate_instance(person, PersonMap)
    assert report.conforms is True
