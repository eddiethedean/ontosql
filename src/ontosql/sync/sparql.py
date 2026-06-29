"""SparqlModel graph sync adapter for OntoSQL."""

from __future__ import annotations

from typing import Any

from triplemodel.store.terms import term_str

from ontosql.mapping.registry import MapperRegistry
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import OntoModel, build_instance_iri
from ontosql.sync.graph import GraphSyncMode, sync_instance_to_store


class OntoGraphSync:
    """Push/pull semantic instances to a SparqlModel SPARQLSession graph."""

    def __init__(
        self,
        sparql_session: Any,
        *,
        maps: list[type[Any]] | None = None,
        registry: PrefixRegistry | None = None,
        mode: GraphSyncMode = "patch",
    ) -> None:
        self._session = sparql_session
        self._registry = registry or PrefixRegistry()
        self._mode = mode
        self._mappers = MapperRegistry()
        if maps:
            self._mappers.register_many(maps)

    def push(
        self,
        instance: OntoModel,
        *,
        prior_nested_iris: set[str] | frozenset[str] | None = None,
    ) -> None:
        """Push a semantic instance into the SPARQL session store."""
        mapper_cls = self._mappers.get(type(instance))
        prior = set(prior_nested_iris) if prior_nested_iris is not None else None
        sync_instance_to_store(
            instance,
            self._session._store.graph,
            mode=self._mode,
            registry=self._registry,
            mapper_cls=mapper_cls,
            prior_nested_iris=prior,
        )

    def pull(
        self,
        entity_type: type[OntoModel],
        *,
        iri: str,
    ) -> OntoModel | None:
        """Hydrate a semantic instance from the SPARQL session graph."""
        from ontosql.import_.hydrate import graph_to_instance

        mapper_cls = self._mappers.get(entity_type)
        graph = self._session._store.graph
        found = any(term_str(triple[0]) == iri for triple in graph)
        if not found:
            return None
        return graph_to_instance(
            graph,
            mapper_cls,
            iri=iri,
            registry=self._registry,
        )

    def instance_iri(self, instance: OntoModel) -> str:
        """Return the canonical IRI for an instance."""
        return build_instance_iri(instance, self._registry)
