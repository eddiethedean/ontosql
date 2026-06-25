"""Async CRUD with AsyncOntoSession (SQLite + aiosqlite)."""

from __future__ import annotations

import asyncio

import _bootstrap  # noqa: F401
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, SQLModel

from models import OrgRow, OrganizationMap, Person, PersonMap, PersonRow
from ontosql import AsyncOntoSession


def _seed_sync(connection) -> None:
    with Session(bind=connection) as raw:
        raw.add(OrgRow(id=10, name="Analytical Engines Inc."))
        raw.add(PersonRow(id=1, name="Ada Lovelace", org_id=10))
        raw.commit()


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_seed_sync)

    async with AsyncOntoSession(engine, maps=[PersonMap, OrganizationMap]) as session:
        ada = await session.get(Person, id=1)
        assert ada is not None
        print(f"Async read: {ada.name}")

        ada.name = "Ada L. Lovelace"
        ada = await session.save(ada)
        print(f"Async updated: {ada.name}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
