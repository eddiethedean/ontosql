"""Tests for PrefixRegistry."""

from __future__ import annotations

import pytest

from ontosql.registry import DEFAULT_PREFIXES, PrefixRegistry


def test_default_prefixes() -> None:
    reg = PrefixRegistry()
    assert "schema" in reg.prefixes()


def test_expand_curie() -> None:
    reg = PrefixRegistry()
    assert reg.expand("schema:name") == "https://schema.org/name"


def test_expand_absolute_iri() -> None:
    reg = PrefixRegistry()
    iri = "http://custom.example/item"
    assert reg.expand(iri) == iri


def test_expand_unknown_prefix() -> None:
    reg = PrefixRegistry()
    with pytest.raises(KeyError):
        reg.expand("unknown:term")


def test_compact_iri() -> None:
    reg = PrefixRegistry()
    assert reg.compact("https://schema.org/name") == "schema:name"


def test_with_prefix_chain() -> None:
    reg = PrefixRegistry().with_prefix("ex", "http://example.org/")
    assert reg.expand("ex:Thing") == "http://example.org/Thing"


def test_context_dict() -> None:
    reg = PrefixRegistry().with_vocab("http://example.org/")
    ctx = reg.context_dict()
    assert ctx["schema"] == DEFAULT_PREFIXES["schema"]
    assert ctx["@vocab"] == "http://example.org/"


def test_freeze_immutable() -> None:
    reg = PrefixRegistry().freeze()
    with pytest.raises(RuntimeError):
        reg.with_prefix("ex", "http://example.org/")


def test_compact_no_match() -> None:
    reg = PrefixRegistry(prefixes={"short": "http://a/"})
    assert reg.compact("http://totally.other/x") == "http://totally.other/x"


def test_custom_prefixes() -> None:
    reg = PrefixRegistry(prefixes={"ex": "http://example.org/"})
    assert reg.prefixes()["ex"] == "http://example.org/"


def test_expand_with_vocab_local_name() -> None:
    reg = PrefixRegistry().with_vocab("http://example.org/")
    assert reg.expand("Thing") == "http://example.org/Thing"


def test_expand_local_name_without_vocab() -> None:
    reg = PrefixRegistry()
    assert reg.expand("Thing") == "Thing"


def test_frozen_with_vocab_raises() -> None:
    reg = PrefixRegistry().freeze()
    with pytest.raises(RuntimeError):
        reg.with_vocab("http://example.org/")


def test_registry_repr_and_copy() -> None:
    reg = PrefixRegistry(prefixes={"ex": "http://example.org/"})
    assert "PrefixRegistry" in repr(reg)
    clone = reg.__copy__()
    assert clone == reg
    assert PrefixRegistry() != object()
