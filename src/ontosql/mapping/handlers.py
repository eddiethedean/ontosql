"""Map-type discovery handlers for OntoMapper.__init_subclass__."""

from __future__ import annotations

from typing import Any, Protocol

from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import CollectionMap, ColumnMap, ComputedMap, NestedMap


class MapHandler(Protocol):
    map_type: type[Any]

    def discover(self, name: str, value: Any) -> tuple[str, Any] | None: ...

    def validate_mapper(self, mapper_cls: type[Any]) -> None: ...


class ColumnMapHandler:
    map_type = ColumnMap

    def discover(self, name: str, value: Any) -> tuple[str, Any] | None:
        if not isinstance(value, ColumnMap):
            return None
        return (
            "column",
            ColumnMap(
                semantic_field=name,
                column=value.column,
                property_curie=value.property_curie,
            ),
        )

    def validate_mapper(self, mapper_cls: type[Any]) -> None:
        if not mapper_cls.column_maps:
            return
        first = next(iter(mapper_cls.column_maps.values()))
        mapper_cls.primary_table = first.column.table
        root_name = first.table_name
        for cmap in mapper_cls.column_maps.values():
            if cmap.table_name != root_name:
                raise ValueError(
                    f"OntoMapper {mapper_cls.__name__}: all column maps must share the same "
                    f"root table (got {root_name!r} and {cmap.table_name!r})"
                )


class NestedMapHandler:
    map_type = NestedMap

    def discover(self, name: str, value: Any) -> tuple[str, Any] | None:
        if not isinstance(value, NestedMap):
            return None
        return (
            "nested",
            NestedMap(
                semantic_field=name,
                entity_type=value.entity_type,
                join=value.join,
                nested_mapper=value.nested_mapper,
                property_curie=value.property_curie,
                cascade=value.cascade,
                fk_column=value.fk_column,
            ),
        )

    def validate_mapper(self, mapper_cls: type[Any]) -> None:
        for nmap in mapper_cls.nested_maps.values():
            if nmap.cascade is not CascadePolicy.IGNORE and nmap.fk_column is None:
                raise ValueError(
                    f"OntoMapper {mapper_cls.__name__}: nested field {nmap.semantic_field!r} "
                    f"requires fk_column= when cascade is {nmap.cascade.value!r}"
                )


class ComputedMapHandler:
    map_type = ComputedMap

    def discover(self, name: str, value: Any) -> tuple[str, Any] | None:
        if not isinstance(value, ComputedMap):
            return None
        return (
            "computed",
            ComputedMap(
                semantic_field=value.semantic_field,
                expression=value.expression,
                property_curie=value.property_curie,
            ),
        )

    def validate_mapper(self, mapper_cls: type[Any]) -> None:
        return None


class CollectionMapHandler:
    map_type = CollectionMap

    def discover(self, name: str, value: Any) -> tuple[str, Any] | None:
        if not isinstance(value, CollectionMap):
            return None
        return (
            "collection",
            CollectionMap(
                semantic_field=name,
                entity_type=value.entity_type,
                through=value.through,
                source_fk=value.source_fk,
                target_fk=value.target_fk,
                nested_mapper=value.nested_mapper,
                property_curie=value.property_curie,
                cascade=value.cascade,
            ),
        )

    def validate_mapper(self, mapper_cls: type[Any]) -> None:
        return None


MAP_HANDLERS: tuple[MapHandler, ...] = (
    ColumnMapHandler(),
    NestedMapHandler(),
    ComputedMapHandler(),
    CollectionMapHandler(),
)

_KIND_ATTR = {
    "column": "column_maps",
    "nested": "nested_maps",
    "computed": "computed_maps",
    "collection": "collection_maps",
}


def discover_maps(cls: type[Any]) -> None:
    """Populate column/nested/computed/collection maps on a mapper subclass."""
    column_maps: dict[str, ColumnMap] = {}
    nested_maps: dict[str, NestedMap] = {}
    computed_maps: dict[str, ComputedMap] = {}
    collection_maps: dict[str, CollectionMap] = {}
    buckets = {
        "column": column_maps,
        "nested": nested_maps,
        "computed": computed_maps,
        "collection": collection_maps,
    }
    for name, value in vars(cls).items():
        for handler in MAP_HANDLERS:
            discovered = handler.discover(name, value)
            if discovered is not None:
                kind, mapped = discovered
                buckets[kind][name] = mapped  # type: ignore[index]
                break
    cls.column_maps = column_maps
    cls.nested_maps = nested_maps
    cls.computed_maps = computed_maps
    cls.collection_maps = collection_maps


def validate_mapper_subclass(cls: type[Any]) -> None:
    semantic_fields: list[str] = []
    semantic_fields.extend(cmap.semantic_field for cmap in cls.column_maps.values())
    semantic_fields.extend(nmap.semantic_field for nmap in cls.nested_maps.values())
    semantic_fields.extend(cmap.semantic_field for cmap in cls.computed_maps.values())
    semantic_fields.extend(cmap.semantic_field for cmap in cls.collection_maps.values())
    if len(semantic_fields) != len(set(semantic_fields)):
        raise ValueError(
            f"OntoMapper {cls.__name__}: duplicate semantic field names across column, "
            f"nested, and computed maps"
        )
    for handler in MAP_HANDLERS:
        handler.validate_mapper(cls)
    if cls.column_maps:
        ColumnMapHandler().validate_mapper(cls)
    elif cls.nested_maps:
        raise ValueError(f"OntoMapper {cls.__name__}: requires at least one column map")
    else:
        raise ValueError(f"OntoMapper {cls.__name__}: requires at least one column map")
