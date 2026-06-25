"""Validate semantic instance graphs with pySHACL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from triplemodel import Store

from ontosql.export.instance import instance_to_graph
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel
from ontosql.shacl.generate import shapes_from_mapper


@dataclass(frozen=True)
class ValidationReport:
    """Result of SHACL validation."""

    conforms: bool
    message: str


def validate_instance(
    instance: OntoModel,
    mapper_cls: type[Any],
    *,
    shapes: Store | None = None,
    registry: PrefixRegistry | None = None,
) -> ValidationReport:
    """Validate an exported instance graph against mapper-derived SHACL shapes."""
    try:
        import pyshacl
    except ImportError as exc:
        raise ImportError(
            "pyshacl is required for SHACL validation. Install with: pip install ontosql[shacl]"
        ) from exc

    data_graph = instance_to_graph(instance, registry=registry)
    shacl_graph = shapes or shapes_from_mapper(mapper_cls, registry=registry)

    data_bytes = data_graph.serialize(format="turtle")
    shacl_bytes = shacl_graph.serialize(format="turtle")

    conforms, results_graph, results_text = pyshacl.validate(
        data_bytes,
        shacl_graph=shacl_bytes,
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=False,
        js=False,
        debug=False,
    )
    message = results_text.decode("utf-8") if isinstance(results_text, bytes) else str(results_text)
    return ValidationReport(conforms=bool(conforms), message=message)
