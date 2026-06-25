"""Prefix registry for CURIE expansion and JSON-LD @context."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from triplemodel import expand_curie

DEFAULT_PREFIXES: dict[str, str] = {
    "schema": "https://schema.org/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "sh": "http://www.w3.org/ns/shacl#",
}

CURATED_PREFIXES: dict[str, dict[str, str]] = {
    "schema_org": dict(DEFAULT_PREFIXES),
    "dcterms": {
        **DEFAULT_PREFIXES,
        "dcterms": "http://purl.org/dc/terms/",
        "dc": "http://purl.org/dc/elements/1.1/",
    },
}


class PrefixRegistry:
    """Manage namespace prefixes for CURIEs and JSON-LD contexts."""

    __slots__ = ("_prefixes", "_frozen", "_vocab")

    def __init__(
        self,
        prefixes: dict[str, str] | None = None,
        *,
        vocab: str | None = None,
    ) -> None:
        self._prefixes: dict[str, str] = dict(DEFAULT_PREFIXES)
        if prefixes:
            self._prefixes.update(prefixes)
        self._vocab: str | None = vocab
        self._frozen = False

    @classmethod
    def curated(
        cls,
        bundle: str = "schema_org",
        *,
        extra: dict[str, str] | None = None,
        vocab: str | None = None,
    ) -> PrefixRegistry:
        """Build a registry from a curated vocabulary bundle."""
        if bundle not in CURATED_PREFIXES:
            known = sorted(CURATED_PREFIXES)
            raise KeyError(f"Unknown prefix bundle {bundle!r}; choose from {known}")
        prefixes = dict(CURATED_PREFIXES[bundle])
        if extra:
            prefixes.update(extra)
        return cls(prefixes, vocab=vocab)

    def with_prefix(self, prefix: str, iri: str) -> PrefixRegistry:
        """Return a new registry with an additional prefix (copy-on-write)."""
        if self._frozen:
            raise RuntimeError("Cannot modify a frozen PrefixRegistry")
        clone = PrefixRegistry()
        clone._prefixes = dict(self._prefixes)
        clone._prefixes[prefix] = iri
        clone._vocab = self._vocab
        return clone

    def with_vocab(self, vocab: str) -> PrefixRegistry:
        """Return a new registry with @vocab set."""
        if self._frozen:
            raise RuntimeError("Cannot modify a frozen PrefixRegistry")
        clone = PrefixRegistry()
        clone._prefixes = dict(self._prefixes)
        clone._vocab = vocab
        return clone

    def freeze(self) -> PrefixRegistry:
        """Return an immutable copy of this registry."""
        frozen = PrefixRegistry()
        frozen._prefixes = dict(self._prefixes)
        frozen._vocab = self._vocab
        frozen._frozen = True
        return frozen

    def expand(self, curie: str) -> str:
        """Expand a CURIE (prefix:local) to a full IRI."""
        if "://" in curie or curie.startswith("urn:"):
            return curie
        if ":" not in curie:
            if self._vocab:
                return f"{self._vocab.rstrip('/')}/{curie}"
            return curie
        try:
            return expand_curie(curie, self._prefixes)
        except ValueError as exc:
            prefix = curie.split(":", 1)[0]
            raise KeyError(f"Unknown prefix: {prefix!r}") from exc

    def compact(self, iri: str) -> str:
        """Compact a full IRI to a CURIE when a known prefix matches."""
        if "://" not in iri:
            return iri
        best_prefix = ""
        best_iri = ""
        for prefix, base in sorted(self._prefixes.items(), key=lambda x: len(x[1]), reverse=True):
            if iri.startswith(base) and len(base) > len(best_iri):
                best_prefix = prefix
                best_iri = base
        if best_prefix:
            local = iri[len(best_iri) :]
            return f"{best_prefix}:{local}"
        return iri

    def context_dict(self) -> dict[str, Any]:
        """Build a JSON-LD @context object."""
        ctx: dict[str, Any] = dict(self._prefixes)
        if self._vocab is not None:
            ctx["@vocab"] = self._vocab
        return ctx

    def prefixes(self) -> dict[str, str]:
        """Return a copy of registered prefixes (without @vocab)."""
        return dict(self._prefixes)

    def __repr__(self) -> str:
        return f"PrefixRegistry(prefixes={self._prefixes!r}, vocab={self._vocab!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrefixRegistry):
            return NotImplemented
        return self._prefixes == other._prefixes and self._vocab == other._vocab

    def __copy__(self) -> PrefixRegistry:
        clone = PrefixRegistry()
        clone._prefixes = deepcopy(self._prefixes)
        clone._vocab = self._vocab
        clone._frozen = self._frozen
        return clone
