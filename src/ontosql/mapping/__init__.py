"""Declarative SQL mappings for semantic entities."""

from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import (
    CollectionMap,
    ColumnMap,
    ComputedMap,
    Map,
    NestedMap,
    collection,
    column,
    computed,
    nested,
)
from ontosql.mapping.mapper import OntoMapper
from ontosql.mapping.registry import MapperRegistry

__all__ = [
    "CascadePolicy",
    "ColumnMap",
    "CollectionMap",
    "ComputedMap",
    "Map",
    "MapperRegistry",
    "NestedMap",
    "OntoMapper",
    "collection",
    "column",
    "computed",
    "nested",
]
