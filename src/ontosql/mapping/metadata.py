"""MapperMetadata implementation for OntoMapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ontosql.mapping.cascade import CascadePolicy
from ontosql.ports.mapper import MapperField


@dataclass(frozen=True)
class MapperMetadataView:
    """Neutral metadata view over an OntoMapper class."""

    mapper_cls: type[Any]

    @property
    def entity(self) -> type[Any]:
        return self.mapper_cls.entity

    @property
    def identity_field(self) -> str:
        return self.mapper_cls.identity_field

    def fields(self) -> list[MapperField]:
        result: list[MapperField] = []
        for name, cmap in self.mapper_cls.column_maps.items():
            if name in self.mapper_cls.nested_maps:
                continue
            result.append(
                MapperField(
                    name=name,
                    kind="column",
                    property_curie=cmap.property_curie,
                )
            )
        for name, nmap in self.mapper_cls.nested_maps.items():
            result.append(
                MapperField(
                    name=name,
                    kind="nested",
                    property_curie=nmap.property_curie,
                    nested_mapper=nmap.nested_mapper,
                    cascade=nmap.cascade,
                )
            )
        for name, cmap in self.mapper_cls.computed_maps.items():
            result.append(
                MapperField(
                    name=name,
                    kind="computed",
                    property_curie=cmap.property_curie,
                )
            )
        for name, cmap in self.mapper_cls.collection_maps.items():
            result.append(
                MapperField(
                    name=name,
                    kind="collection",
                    property_curie=cmap.property_curie,
                    nested_mapper=cmap.nested_mapper,
                    cascade=cmap.cascade,
                )
            )
        return result

    def column_field_names(self) -> list[str]:
        return [
            name for name in self.mapper_cls.column_maps if name not in self.mapper_cls.nested_maps
        ]

    def nested_field_names(self) -> list[str]:
        return list(self.mapper_cls.nested_maps.keys())

    def collection_field_names(self) -> list[str]:
        return list(self.mapper_cls.collection_maps.keys())

    def field_kind(self, name: str) -> Literal["column", "nested", "computed", "collection"] | None:
        if name in self.mapper_cls.nested_maps:
            return "nested"
        if name in self.mapper_cls.collection_maps:
            return "collection"
        if name in self.mapper_cls.computed_maps:
            return "computed"
        if name in self.mapper_cls.column_maps:
            return "column"
        return None

    def nested_mapper_for(self, field_name: str) -> type[Any] | None:
        if field_name in self.mapper_cls.nested_maps:
            return self.mapper_cls.nested_maps[field_name].nested_mapper
        if field_name in self.mapper_cls.collection_maps:
            return self.mapper_cls.collection_maps[field_name].nested_mapper
        return None

    def cascade_for(self, field_name: str) -> CascadePolicy | None:
        if field_name in self.mapper_cls.nested_maps:
            return self.mapper_cls.nested_maps[field_name].cascade
        if field_name in self.mapper_cls.collection_maps:
            return self.mapper_cls.collection_maps[field_name].cascade
        return None


def mapper_metadata(mapper_cls: type[Any]) -> MapperMetadataView:
    return MapperMetadataView(mapper_cls)
