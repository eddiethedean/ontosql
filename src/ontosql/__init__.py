"""OntoSQL — semantic data access for SQL."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from ontosql.import_.hydrate import OntoImportError
from ontosql.io import from_jsonld, to_jsonld, to_rdf
from ontosql.mapping import CascadePolicy, Map, OntoMapper
from ontosql.ports import GraphSyncPort, MapperLookup, MapperMetadata, PlanExecutor
from ontosql.registry import PrefixRegistry
from ontosql.semantic import OntoModel, onto_property
from ontosql.session import (
    AsyncOntoSession,
    GraphSyncError,
    OntoSession,
    Page,
    paginate,
    paginate_async,
)
from ontosql.sync.graph import GraphSyncMode

try:
    __version__ = version("ontosql")
except PackageNotFoundError:
    __version__ = "0.5.0"

__all__ = [
    "AsyncOntoSession",
    "CascadePolicy",
    "GraphSyncError",
    "GraphSyncMode",
    "GraphSyncPort",
    "Map",
    "MapperLookup",
    "MapperMetadata",
    "OntoImportError",
    "OntoMapper",
    "OntoModel",
    "OntoSession",
    "Page",
    "PlanExecutor",
    "PrefixRegistry",
    "__version__",
    "from_jsonld",
    "onto_property",
    "paginate",
    "paginate_async",
    "to_jsonld",
    "to_rdf",
]
