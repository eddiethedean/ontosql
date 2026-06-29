"""SQL plan execution port."""

from __future__ import annotations

from typing import Any, Protocol

from ontosql.compile.plan import DeletePlan, WritePlan


class PlanExecutor(Protocol):
    """Execute compiled write/delete plans against a database session."""

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
