"""Graph sync port."""

from __future__ import annotations

from typing import Protocol

from triplemodel import Store


class GraphSyncPort(Protocol):
    """Backing store that accepts incremental graph updates."""

    @property
    def graph(self) -> Store: ...

    def update_graph(
        self,
        *,
        add: Store | None = None,
        remove: Store | None = None,
    ) -> None: ...
