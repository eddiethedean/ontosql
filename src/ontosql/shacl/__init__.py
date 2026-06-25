"""SHACL shape generation and validation for OntoSQL."""

from ontosql.shacl.generate import shapes_from_mapper, shapes_from_mappers
from ontosql.shacl.validate import ValidationReport, validate_instance

__all__ = [
    "ValidationReport",
    "shapes_from_mapper",
    "shapes_from_mappers",
    "validate_instance",
]
