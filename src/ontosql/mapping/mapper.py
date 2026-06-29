"""OntoMapper base class."""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from ontosql.mapping.handlers import discover_maps, validate_mapper_subclass
from ontosql.mapping.map import CollectionMap, ColumnMap, ComputedMap, NestedMap
from ontosql.mapping.metadata import MapperMetadataView, mapper_metadata
from ontosql.mapping.registry import MapperRegistry
from ontosql.semantic.model import OntoModel

E = TypeVar("E", bound=OntoModel)


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
        discover_maps(cls)
        validate_mapper_subclass(cls)

    @classmethod
    def metadata(cls) -> MapperMetadataView:
        """Neutral metadata view for RDF/import/sync layers."""
        return mapper_metadata(cls)

    @classmethod
    def for_entity(cls, entity_type: type[E], *, registry: MapperRegistry) -> type[OntoMapper[E]]:
        return registry.get(entity_type)  # type: ignore[return-value]

    @classmethod
    def identity_column(cls) -> Any:
        identity = cls.identity_field
        if identity not in cls.column_maps:
            raise ValueError(
                f"Mapper {cls.__name__} has no column map for identity field {identity!r}"
            )
        return cls.column_maps[identity].column
