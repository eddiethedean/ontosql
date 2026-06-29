"""OntoModel and ontology property metadata."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo

from ontosql.registry import PrefixRegistry
from ontosql.semantic.meta import OntoModelMeta

ONTO_META_KEY = "ontosql"


class OntoModel(BaseModel, metaclass=OntoModelMeta):
    """Base class for semantic entities."""

    model_config = ConfigDict(from_attributes=True)

    type_iri: ClassVar[str | None] = None
    iri_template: ClassVar[str | None] = None
    identity_field: ClassVar[str] = "id"
    jsonld_context: ClassVar[dict[str, Any] | None] = None
    """Optional JSON-LD ``@context`` for list/export endpoints (see SPECS)."""

    def to_jsonld(self, registry: PrefixRegistry | None = None) -> dict[str, Any]:
        """Export this instance as a JSON-LD document (via ``ontosql.io``)."""
        from ontosql.io import to_jsonld

        return to_jsonld(self, registry=registry)

    def to_rdf(self, *, format: str = "turtle", registry: PrefixRegistry | None = None) -> str:
        """Export this instance as an RDF serialization (via ``ontosql.io``)."""
        from ontosql.io import to_rdf

        return to_rdf(self, format=format, registry=registry)

    @classmethod
    def from_jsonld(
        cls,
        doc: dict[str, Any],
        *,
        mapper: type[Any],
        registry: PrefixRegistry | None = None,
    ) -> OntoModel:
        """Hydrate an instance from a JSON-LD document using a mapper (via ``ontosql.io``)."""
        from ontosql.io import from_jsonld

        return from_jsonld(cls, doc, mapper=mapper, registry=registry)


def onto_property(
    curie: str,
    *,
    datatype: str | None = None,
    iri: str | None = None,
    language: str | None = None,
    **field_kwargs: Any,
) -> Any:
    """Attach ontology metadata to a semantic model field."""
    meta: dict[str, Any] = {"ontology": curie}
    if datatype is not None:
        meta["datatype"] = datatype
    if iri is not None:
        meta["iri"] = iri
    if language is not None:
        meta["language"] = language

    extra = field_kwargs.pop("json_schema_extra", None)
    js_extra: dict[str, Any] = dict(extra) if isinstance(extra, dict) else {}
    js_extra[ONTO_META_KEY] = meta
    return Field(**field_kwargs, json_schema_extra=js_extra)


def get_onto_property_meta(model_cls: type[OntoModel], field_name: str) -> dict[str, Any]:
    """Extract ontology metadata for a semantic field."""
    info = model_cls.model_fields.get(field_name)
    if info is None:
        return {}
    return _meta_from_field_info(info)


def _meta_from_field_info(field_info: FieldInfo) -> dict[str, Any]:
    extra = field_info.json_schema_extra
    if extra is None or callable(extra) or not isinstance(extra, dict):
        return {}
    meta = extra.get(ONTO_META_KEY)
    if isinstance(meta, dict):
        return dict(meta)
    return {}


def iter_onto_fields(model_cls: type[OntoModel]) -> list[tuple[str, FieldInfo]]:
    """Yield (name, FieldInfo) for all semantic fields."""
    return list(model_cls.model_fields.items())


def build_instance_iri(
    instance: OntoModel,
    registry: PrefixRegistry | None = None,
) -> str:
    """Build instance IRI from class template or fallback pattern."""
    model_cls = type(instance)
    template = model_cls.iri_template
    if template:
        values = {name: getattr(instance, name, None) for name in model_cls.model_fields}
        try:
            return template.format(**values)
        except (KeyError, ValueError):
            pass
    pk = getattr(instance, model_cls.identity_field, None)
    class_name = model_cls.__name__.lower()
    return f"http://example.org/{class_name}/{pk}"


def parse_iri_id(iri: str, model_cls: type[OntoModel]) -> int | str | None:
    """Extract identity value from IRI using template (0.2: single {id} placeholder)."""
    template = model_cls.iri_template
    if not template or "{id}" not in template:
        return None
    prefix, suffix = template.split("{id}", 1)
    if not iri.startswith(prefix) or not iri.endswith(suffix):
        return None
    raw = iri[len(prefix) : len(iri) - len(suffix)]
    identity_field = model_cls.identity_field
    field_info = model_cls.model_fields.get(identity_field)
    if field_info and field_info.annotation is int:
        try:
            return int(raw)
        except ValueError:
            return None
    return raw
