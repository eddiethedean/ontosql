"""OntoMapper base class."""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import CollectionMap, ColumnMap, ComputedMap, NestedMap
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel

E = TypeVar("E", bound=OntoModel)

_global_registry = MapperRegistry()


class OntoMapper(Generic[E]):
    """Declares how a semantic entity maps to SQL tables."""

    entity: ClassVar[type[Any]]
    identity_field: ClassVar[str] = "id"

    column_maps: ClassVar[dict[str, ColumnMap]]
    nested_maps: ClassVar[dict[str, NestedMap]]
    computed_maps: ClassVar[dict[str, ComputedMap]]
    collection_maps: ClassVar[dict[str, CollectionMap]]
    primary_table: ClassVar[Any]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "entity" not in cls.__dict__:
            return
        column_maps: dict[str, ColumnMap] = {}
        nested_maps: dict[str, NestedMap] = {}
        computed_maps: dict[str, ComputedMap] = {}
        collection_maps: dict[str, CollectionMap] = {}
        for name, value in vars(cls).items():
            if isinstance(value, ColumnMap):
                column_maps[name] = ColumnMap(
                    semantic_field=name,
                    column=value.column,
                    property_curie=value.property_curie,
                )
            elif isinstance(value, NestedMap):
                nested_maps[name] = NestedMap(
                    semantic_field=name,
                    entity_type=value.entity_type,
                    join=value.join,
                    nested_mapper=value.nested_mapper,
                    property_curie=value.property_curie,
                    cascade=value.cascade,
                    fk_column=value.fk_column,
                )
            elif isinstance(value, ComputedMap):
                computed_maps[name] = ComputedMap(
                    semantic_field=value.semantic_field,
                    expression=value.expression,
                    property_curie=value.property_curie,
                )
            elif isinstance(value, CollectionMap):
                collection_maps[name] = CollectionMap(
                    semantic_field=name,
                    entity_type=value.entity_type,
                    through=value.through,
                    source_fk=value.source_fk,
                    target_fk=value.target_fk,
                    nested_mapper=value.nested_mapper,
                    property_curie=value.property_curie,
                    cascade=value.cascade,
                )
        cls.column_maps = column_maps
        cls.nested_maps = nested_maps
        cls.computed_maps = computed_maps
        cls.collection_maps = collection_maps
        semantic_fields: list[str] = []
        semantic_fields.extend(cmap.semantic_field for cmap in column_maps.values())
        semantic_fields.extend(nmap.semantic_field for nmap in nested_maps.values())
        semantic_fields.extend(cmap.semantic_field for cmap in computed_maps.values())
        semantic_fields.extend(cmap.semantic_field for cmap in collection_maps.values())
        if len(semantic_fields) != len(set(semantic_fields)):
            raise ValueError(
                f"OntoMapper {cls.__name__}: duplicate semantic field names across column, "
                f"nested, and computed maps"
            )
        for nmap in nested_maps.values():
            if nmap.cascade is not CascadePolicy.IGNORE and nmap.fk_column is None:
                raise ValueError(
                    f"OntoMapper {cls.__name__}: nested field {nmap.semantic_field!r} "
                    f"requires fk_column= when cascade is {nmap.cascade.value!r}"
                )
        if column_maps:
            first = next(iter(column_maps.values()))
            cls.primary_table = first.column.table
            root_name = first.table_name
            for cmap in column_maps.values():
                if cmap.table_name != root_name:
                    raise ValueError(
                        f"OntoMapper {cls.__name__}: all column maps must share the same "
                        f"root table (got {root_name!r} and {cmap.table_name!r})"
                    )
        elif nested_maps:
            raise ValueError(f"OntoMapper {cls.__name__}: requires at least one column map")
        else:
            raise ValueError(f"OntoMapper {cls.__name__}: requires at least one column map")

    @classmethod
    def for_entity(
        cls, entity_type: type[E], registry: MapperRegistry | None = None
    ) -> type[OntoMapper[E]]:
        reg = registry or _global_registry
        return reg.get(entity_type)  # type: ignore[return-value]

    @classmethod
    def identity_column(cls) -> Any:
        identity = cls.identity_field
        if identity not in cls.column_maps:
            raise ValueError(
                f"Mapper {cls.__name__} has no column map for identity field {identity!r}"
            )
        return cls.column_maps[identity].column
