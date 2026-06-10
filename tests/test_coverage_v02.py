"""Additional tests for full coverage of 0.2 modules."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import column
from sqlmodel import Field, SQLModel

from ontosql import OntoModel
from ontosql.compile.select import compile_select_plan
from ontosql.fastapi.negotiate import negotiate_onto_response
from ontosql.fastapi.responses import JSONLDResponse, RDFResponse, _dumps_json, _serialize_data
from ontosql.mapping.map import ColumnMap, Map, _column_field_name
from ontosql.mapping.mapper import OntoMapper, get_global_registry
from ontosql.mapping.registry import MapperRegistry
from ontosql.query.expr import OrExpr, compile_expr
from ontosql.registry import PrefixRegistry
from ontosql.semantic.model import build_instance_iri, onto_property, parse_iri_id
from ontosql.session.async_session import AsyncOntoSession
from ontosql.session.hydrate import _row_get, hydrate_first, hydrate_row
from ontosql.session.sync import OntoSession
from tests.models import Organization, OrganizationMap, Person, PersonMap, PersonRow

pytest.importorskip("fastapi")


def test_plan_label_for() -> None:
    plan = compile_select_plan(PersonMap)
    assert plan.label_for("id") == "people_id"
    assert plan.label_for("id", nested="employer") == "employer_orgs_id"
    with pytest.raises(KeyError):
        plan.label_for("missing")


def test_compile_get_by_iri_invalid() -> None:
    with pytest.raises(ValueError, match="Cannot parse IRI"):
        compile_select_plan(PersonMap, iri="not-a-valid-iri")


def test_compile_order_by() -> None:
    plan = compile_select_plan(PersonMap, order_by=Person.name)
    assert plan.select is not None


def test_column_field_name_fallback() -> None:
    col = column("x")
    assert _column_field_name(col) == "x"


def test_mapper_for_entity_and_identity() -> None:
    reg = MapperRegistry()
    reg.register_many([PersonMap, OrganizationMap])
    assert OntoMapper.for_entity(Person, registry=reg) is PersonMap
    assert PersonMap.identity_column() is not None


def test_mapper_identity_missing() -> None:
    class X(SQLModel, table=True):
        __tablename__ = "x"
        id: int | None = Field(default=None, primary_key=True)
        n: str

    class XEnt(OntoModel):
        id: int
        n: str

    class XMap(OntoMapper[XEnt]):
        entity = XEnt
        n = Map(X.n)

    with pytest.raises(ValueError, match="identity field"):
        XMap.identity_column()


def test_mapper_multi_table_error() -> None:
    class A(SQLModel, table=True):
        __tablename__ = "a"
        id: int | None = Field(default=None, primary_key=True)

    class B(SQLModel, table=True):
        __tablename__ = "b"
        id: int | None = Field(default=None, primary_key=True)

    class E(OntoModel):
        id: int
        bid: int

    with pytest.raises(ValueError, match="same root table"):

        class Bad(OntoMapper[E]):
            entity = E
            id = Map(A.id)
            bid = Map(B.id)


def test_nested_map_target_table() -> None:
    nmap = PersonMap.nested_maps["employer"]
    assert nmap.target_table is OrganizationMap.primary_table


def test_column_map_no_table() -> None:
    col = column("x")
    cmap = ColumnMap("x", col)
    with pytest.raises(ValueError, match="no table"):
        _ = cmap.table_name


def test_query_operators() -> None:
    col = column("name")
    resolve = lambda ref: col  # noqa: E731
    compile_expr(Person.name != "x", resolve)
    compile_expr(Person.name < "x", resolve)
    compile_expr(Person.name <= "x", resolve)
    compile_expr(Person.name > "x", resolve)
    compile_expr(Person.name >= "x", resolve)
    compile_expr(Person.name.in_(["a", "b"]), resolve)
    compile_expr(Person.name.is_null(), resolve)
    compile_expr(OrExpr((Person.name.startswith("A"), Person.name == "B")), resolve)


def test_registry_vocab_and_copy() -> None:
    reg = PrefixRegistry()
    assert reg.expand("local") == "local"
    reg2 = reg.with_vocab("http://vocab.example/")
    assert reg2.expand("term") == "http://vocab.example/term"
    frozen = reg.freeze()
    with pytest.raises(RuntimeError):
        frozen.with_vocab("http://x/")
    assert reg == PrefixRegistry()
    from copy import copy

    copy(reg)


def test_onto_property_all_keys() -> None:
    class M(OntoModel):
        id: int
        x: str = onto_property(
            "schema:x",
            datatype="xsd:string",
            iri="http://ex/x",
            language="en",
            graph="http://ex/g",
        )

    assert M.model_fields["x"].json_schema_extra is not None


def test_build_iri_fallback() -> None:
    class NoTemplate(OntoModel):
        id: int
        name: str

    assert "notemplate" in build_instance_iri(NoTemplate(id=1, name="a"))


def test_parse_iri_non_int() -> None:
    class StrId(OntoModel):
        type_iri = "schema:Thing"
        iri_template = "http://ex/{id}"
        id: str
        name: str

    assert parse_iri_id("http://ex/abc", StrId) == "abc"


def test_hydrate_row_mapping() -> None:
    plan = compile_select_plan(PersonMap, id_value=1)
    row = {
        "people_id": 1,
        "people_name": "Ada",
        "employer_orgs_id": None,
        "employer_orgs_name": None,
    }
    person = hydrate_row(plan, row)
    assert person.employer is None


def test_hydrate_first_empty_and_row() -> None:
    plan = compile_select_plan(PersonMap, id_value=1)

    class EmptyResult:
        def first(self) -> None:
            return None

    assert hydrate_first(plan, EmptyResult()) is None

    class RowResult:
        def __init__(self, row: dict[str, object]) -> None:
            self._row = row

        def first(self) -> dict[str, object]:
            return self._row

    row = {
        "people_id": 1,
        "people_name": "Ada",
        "employer_orgs_id": None,
        "employer_orgs_name": None,
    }
    person = hydrate_first(plan, RowResult(row))
    assert person is not None
    assert person.name == "Ada"


def test_row_get_attr() -> None:
    class Row:
        people_id = 1

    assert _row_get(Row(), "people_id") == 1


def test_sync_session_errors(sync_engine) -> None:
    with OntoSession(sync_engine, maps=[PersonMap]) as session:
        with pytest.raises(ValueError, match="only one"):
            session.get(Person, id=1, iri="http://x")
        session.execute_sql("SELECT 1")


@pytest.mark.asyncio
async def test_async_session_errors(async_engine) -> None:
    session = AsyncOntoSession(async_engine, maps=[PersonMap])
    with pytest.raises(RuntimeError, match="not active"):
        await session.get(Person, id=1)
    async with session:
        with pytest.raises(ValueError, match="requires id="):
            await session.get(Person)


def test_fastapi_serialize_paths() -> None:
    class Exportable:
        def to_jsonld(self) -> dict:
            return {"@id": "x"}

        def to_rdf(self, *, format: str = "turtle") -> str:
            return "@prefix ex: <http://ex/> ."

    body, mt = _serialize_data(Exportable(), "json-ld")
    assert mt == "application/ld+json"
    body, mt = _serialize_data(Exportable(), "turtle")
    assert mt == "text/turtle"
    body, mt = _serialize_data({"@id": "x"}, "json-ld")
    assert body
    body, mt = _serialize_data("ttl text", "turtle")
    assert body == "ttl text"
    with pytest.raises(TypeError):
        _serialize_data(42, "turtle")


def test_fastapi_dumps_json_no_orjson(monkeypatch: pytest.MonkeyPatch) -> None:
    import ontosql.fastapi.responses as resp

    monkeypatch.setattr(resp, "json", __import__("json"))
    monkeypatch.setitem(__import__("sys").modules, "orjson", None)
    out = _dumps_json({"a": 1})
    assert "a" in out


def test_negotiate_fallbacks() -> None:
    request = MagicMock()
    request.headers.get.return_value = None
    resp = negotiate_onto_response(request, {"plain": 1})
    assert resp.media_type == "application/ld+json"


def test_rdf_response_class() -> None:
    r = RDFResponse({"@id": "x"}, format="json-ld")
    assert r.media_type == "application/ld+json"


def test_jsonld_response() -> None:
    r = JSONLDResponse({"@id": "x"})
    assert r.media_type == "application/ld+json"


def test_get_global_registry() -> None:
    assert get_global_registry() is get_global_registry()


def test_map_nested_guess_field() -> None:
    nm = Map.nested(
        Organization,
        join=PersonRow.org_id == PersonRow.org_id,
        nested_map=OrganizationMap,
    )
    assert nm.semantic_field == "organization"
