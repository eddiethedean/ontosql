"""Session backend port for sync/async SQL execution."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.sql import Select

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.ports.plan_executor import PlanExecutor


class SessionBackend(Protocol):
    """Database session operations used by flush coordinator and CRUD paths."""

    @property
    def executor(self) -> PlanExecutor: ...

    def run_select(self, statement: Select[Any]) -> list[Any]: ...

    def execute_write_plan(
        self,
        plan: WritePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None: ...

    def execute_delete_plan(
        self,
        plan: DeletePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
