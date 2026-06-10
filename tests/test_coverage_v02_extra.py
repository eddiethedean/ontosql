"""Edge-case coverage for remaining lines."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ontosql.compile.select import compile_select_plan
from ontosql.fastapi.negotiate import _parse_accept, _parse_accept_params, negotiate_onto_response
from ontosql.fastapi.responses import (
    NTriplesResponse,
    RDFXMLResponse,
    TurtleResponse,
    _serialize_data,
)
from ontosql.mapping.map import Map
from ontosql.mapping.mapper import OntoMapper
from ontosql.query.expr import AndExpr, CompileError, compile_expr
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import _meta_from_field_info, build_instance_iri
from ontosql.session.async_session import AsyncOntoSession
from ontosql.session.hydrate import hydrate_row
from ontosql.session.sync import OntoSession
from tests.models import Organization, OrganizationMap, Person, PersonMap

pytest.importorskip("fastapi")


def test_map_no_field_name() -> None:
    class Anonymous:
        pass

    anon = Anonymous()
    with pytest.raises(ValueError, match="Cannot infer"):
        Map(anon)  # type: ignore[arg-type]


def test_meta_from_field_info() -> None:
    assert _meta_from_field_info(Person.model_fields["id"]) == {}


def test_build_iri_template_error() -> None:
    from ontosql import OntoModel

    class Bad(OntoModel):
        type_iri = "schema:Thing"
        iri_template = "http://ex/{missing}"
        id: int
        name: str

    assert build_instance_iri(Bad(id=1, name="n")) == "http://example.org/bad/1"


def test_compile_unknown_op() -> None:
    from ontosql.query.expr import Comparison

    cmp = Comparison(Person.name, "bogus", "x")
    with pytest.raises(CompileError, match="Unknown comparison"):
        compile_expr(cmp, lambda ref: PersonMap.column_maps["name"].column)


def test_compile_empty_and() -> None:
    with pytest.raises(CompileError, match="Empty AND"):
        compile_expr(AndExpr(()), lambda ref: PersonMap.column_maps["name"].column)


def test_parse_accept_params_empty() -> None:
    assert _parse_accept_params("") == ("", 1.0)


def test_parse_accept_invalid_q() -> None:
    assert _parse_accept_params("text/turtle; q=not-a-number") == ("text/turtle", 1.0)


def test_parse_accept_major_wildcard() -> None:
    assert _parse_accept("application/*") is None


def test_negotiate_orjson_path() -> None:
    request = MagicMock()
    request.headers.get.return_value = "application/ld+json"

    class Exportable:
        def to_jsonld(self) -> dict:
            return {"@id": "x"}

    resp = negotiate_onto_response(request, Exportable())
    assert "json" in resp.media_type


def test_response_classes() -> None:
    TurtleResponse("@prefix ex: <http://ex/> .")
    NTriplesResponse("<s> <p> <o> .")
    RDFXMLResponse(
        '<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"></rdf:RDF>'
    )


def test_hydrate_nested_with_id() -> None:
    from ontosql.compile.select import compile_select_plan

    plan = compile_select_plan(PersonMap, id_value=1)
    row = {
        "people_id": 1,
        "people_name": "Ada",
        "employer_orgs_id": 10,
        "employer_orgs_name": "Org",
    }
    person = hydrate_row(plan, row)
    assert person.employer is not None
    assert person.employer.name == "Org"


def test_registry_unknown_compact() -> None:
    reg = PrefixRegistry()
    iri = "http://unknown.example.org/term"
    assert reg.compact(iri) == iri


def test_registry_get_missing() -> None:
    from ontosql.mapping.registry import MapperRegistry

    reg = MapperRegistry()
    with pytest.raises(KeyError, match="No mapper"):
        reg.get(Person)


def test_compile_column_key_error() -> None:
    from ontosql.compile.select import _column_for_field

    with pytest.raises(KeyError, match="not a column"):
        _column_for_field(PersonMap, Person.employer)


def test_compile_no_primary_table() -> None:
    class FakeMapper:
        __name__ = "Fake"
        primary_table = None
        column_maps = {}
        nested_maps = {}

    with pytest.raises(ValueError, match="no primary_table"):
        compile_select_plan(FakeMapper)  # type: ignore[arg-type]


def test_compile_offset() -> None:
    plan = compile_select_plan(PersonMap, offset=5, limit=1)
    assert "OFFSET" in str(plan.select.compile(compile_kwargs={"literal_binds": True})).upper()


def test_sync_rollback(sync_engine) -> None:
    try:
        with OntoSession(sync_engine, maps=[PersonMap]):
            raise RuntimeError("boom")
    except RuntimeError:
        pass


@pytest.mark.asyncio
async def test_async_rollback(async_engine) -> None:
    try:
        async with AsyncOntoSession(async_engine, maps=[PersonMap]):
            raise RuntimeError("boom")
    except RuntimeError:
        pass


@pytest.mark.asyncio
async def test_async_get_both_ids(async_engine) -> None:
    async with AsyncOntoSession(async_engine, maps=[PersonMap]) as session:
        with pytest.raises(ValueError, match="only one"):
            await session.get(Person, id=1, iri="http://x")


@pytest.mark.asyncio
async def test_async_execute_sql(async_engine) -> None:
    async with AsyncOntoSession(async_engine, maps=[PersonMap]) as session:
        await session.execute_sql("SELECT 1")


def test_hydrate_raises_without_mapper() -> None:
    from ontosql.compile.plan import SelectPlan

    plan = SelectPlan(select=MagicMock(), mapper_cls=None)
    with pytest.raises(ValueError, match="no mapper_cls"):
        hydrate_row(plan, {})


def test_hydrate_nested_null_identity() -> None:
    from ontosql.compile.select import compile_select_plan

    plan = compile_select_plan(PersonMap, id_value=3)
    row = {
        "people_id": 3,
        "people_name": "Solo",
        "employer_orgs_id": None,
        "employer_orgs_name": "Ghost",
    }
    person = hydrate_row(plan, row)
    assert person.employer is None


def test_mapper_init_without_entity() -> None:
    class IncompleteMapper(OntoMapper):
        pass

    assert "column_maps" not in IncompleteMapper.__dict__


def test_mapper_nested_only_raises() -> None:
    from sqlmodel import Field, SQLModel

    from ontosql import OntoModel

    class EmptyRow(SQLModel, table=True):
        __tablename__ = "empty_nested_only"
        id: int | None = Field(default=None, primary_key=True)

    class E(OntoModel):
        id: int
        child: Organization | None = None

    from ontosql.mapping.cascade import CascadePolicy

    with pytest.raises(ValueError, match="requires at least one column map"):

        class OnlyNested(OntoMapper[E]):
            entity = E
            child = Map.nested(
                Organization,
                join=EmptyRow.id == EmptyRow.id,
                nested_map=OrganizationMap,
                cascade=CascadePolicy.IGNORE,
            )


def test_serialize_rdf_from_mixin_only() -> None:
    class RdfOnly:
        def to_rdf(self, *, format: str = "turtle") -> str:
            return "@prefix ex: <http://ex/> ."

    body, mt = _serialize_data(RdfOnly(), "turtle")
    assert mt == "text/turtle"
