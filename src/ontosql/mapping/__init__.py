"""Declarative SQL mappings for semantic entities."""

from ontosql.mapping.cascade import CascadePolicy
from ontosql.mapping.map import ColumnMap, Map, NestedMap
from ontosql.mapping.mapper import OntoMapper
from ontosql.mapping.registry import MapperRegistry

__all__ = ["CascadePolicy", "ColumnMap", "Map", "NestedMap", "OntoMapper", "MapperRegistry"]
