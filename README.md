# SemSQL

**Semantic interoperability for SQLModel** — enrich operational models with ontology metadata and export JSON-LD and RDF without leaving Python.

```bash
pip install semsql
pip install semsql[fastapi]   # optional API helpers
```

## Quick start

```python
from sqlmodel import Field, SQLModel
from semsql import OntoMixin, onto_field, onto_model


@onto_model(type_="schema:Person", iri_template="http://example.org/person/{id}")
class Person(SQLModel, OntoMixin, table=False):
    id: int | None = Field(default=None, primary_key=True)
    name: str = onto_field(ontology="schema:name")


person = Person(id=1, name="Ada Lovelace")
print(person.to_jsonld())
print(person.to_rdf(format="turtle"))
```

## Features (0.1.0)

- `onto_field()` — attach ontology CURIEs/IRIs to model fields
- `onto_model()` — declare RDF type and instance IRI templates on classes
- `PrefixRegistry` — manage namespace prefixes for JSON-LD `@context`
- `to_jsonld()` / `to_rdf()` — export instances to semantic web formats
- FastAPI response helpers with content negotiation (`semsql[fastapi]`)

## FastAPI

```python
from fastapi import FastAPI, Request
from semsql.fastapi import negotiate_onto_response

app = FastAPI()

@app.get("/person/{person_id}")
def get_person(person_id: int, request: Request):
    person = Person(id=person_id, name="Ada Lovelace")
    return negotiate_onto_response(request, person)
```

See [examples/fastapi_demo.py](examples/fastapi_demo.py).

## Limitations (0.1.0)

- No RDF import or SHACL generation yet (planned for 0.2+)
- Foreign-key-only relationships export as `@id` references, not nested objects (use a nested `OntoMixin` field for embedded objects)
- JSON-LD framing requires a future `semsql[jsonld]` extra (PyLD)
- Do not map two fields to the same ontology property; if you do, nested objects are preferred over FK integers (a warning is emitted)

## Documentation

- [Roadmap](docs/ROADMAP.md)
- [Technical specification](docs/SPECS.md)
- [Project plan](docs/PLAN.md)
- [Dependency assessment](docs/DEPS.md)
- [Changelog](CHANGELOG.md)

## Development

See [Releasing](docs/RELEASING.md) for the version publish checklist.

```bash
pip install -e ".[dev]"
ruff check src tests
ruff format src tests
ty check
pytest --cov=semsql --cov-fail-under=100
```

## License

MIT — see [LICENSE](LICENSE).
