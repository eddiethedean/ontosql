"""Tests for paginate helper."""

from __future__ import annotations

import pytest

from ontosql.session.pagination import Page, paginate, paginate_async
from tests.models import Person


def test_paginate_sync(onto_session) -> None:
    page = paginate(onto_session, Person, limit=2, offset=0)
    assert isinstance(page, Page)
    assert len(page.items) == 2
    assert page.total == 3
    assert page.limit == 2
    assert page.offset == 0


def test_paginate_without_total(onto_session) -> None:
    page = paginate(onto_session, Person, limit=10, include_total=False)
    assert page.total is None
    assert len(page.items) == 3


@pytest.mark.asyncio
async def test_paginate_async(async_onto_session) -> None:
    page = await paginate_async(async_onto_session, Person, limit=1, offset=1)
    assert page.total == 2
    assert len(page.items) == 1
