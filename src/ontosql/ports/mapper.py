"""Mapper lookup and metadata protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from ontosql.mapping.cascade import CascadePolicy


@dataclass(frozen=True)
class MapperField:
    """Neutral view of one mapped semantic field."""

    name: str
    kind: Literal["column", "nested", "computed", "collection"]
    property_curie: str | None
    nested_mapper: type[Any] | None = None
    cascade: CascadePolicy | None = None


class MapperLookup(Protocol):
    """Resolve semantic entity types to mapper classes."""

    def get(self, entity_type: type[Any]) -> type[Any]: ...

    def has(self, entity_type: type[Any]) -> bool: ...

    def all_mappers(self) -> list[type[Any]]: ...


class MapperMetadata(Protocol):
    """Iterate mapper fields without reaching into internal dicts."""

    @property
    def entity(self) -> type[Any]: ...

    @property
    def identity_field(self) -> str: ...

    def fields(self) -> list[MapperField]: ...

    def column_field_names(self) -> list[str]: ...

    def nested_field_names(self) -> list[str]: ...

    def collection_field_names(self) -> list[str]: ...
