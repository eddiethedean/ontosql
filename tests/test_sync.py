"""Tests for graph sync."""

from __future__ import annotations

from pyoxigraph import NamedNode
from triplemodel import Store
from triplemodel.store.terms import term_str

from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import build_instance_iri
from ontosql.sync import StoreSyncTarget, push_instance
from ontosql.sync.graph import sync_instance_to_store
from tests.models import Organization, Person, PersonMap


def test_push_instance_replace_mode() -> None:
    person = Person(
        id=1,
        name="Ada Lovelace",
        employer=Organization(id=10, name="Analytical Engines Inc."),
    )
    target = Store()
    push_instance(person, target, mode="replace", mapper_cls=PersonMap)
    reg = PrefixRegistry()
    iri = build_instance_iri(person, reg)
    assert any(term_str(t[0]) == iri for t in target)


def test_store_sync_target() -> None:
    person = Person(id=2, name="Grace", employer=None)
    sync_target = StoreSyncTarget()
    push_instance(person, sync_target, mode="replace", mapper_cls=PersonMap)
    assert len(sync_target.graph) > 0


def test_sync_patch_updates_name() -> None:
    person = Person(id=3, name="Original", employer=None)
    target = Store()
    sync_instance_to_store(person, target, mode="replace", mapper_cls=PersonMap)
    person2 = Person(id=3, name="Updated", employer=None)
    sync_instance_to_store(person2, target, mode="patch", mapper_cls=PersonMap)
    reg = PrefixRegistry()
    subject = build_instance_iri(person2, reg)
    names = [
        str(getattr(o, "value", o))
        for o in target.objects(
            NamedNode(subject),
            NamedNode(reg.expand("schema:name")),
        )
    ]
    assert "Updated" in names
