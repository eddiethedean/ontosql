"""Sync and async session backends wrapping SQLAlchemy and plan executors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from ontosql.compile.execute import (
    async_execute_delete_plan,
    async_execute_write_plan,
    execute_delete_plan,
    execute_write_plan,
)
from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.ports.plan_executor import PlanExecutor


@dataclass
class SyncPlanExecutor:
    """Default sync plan executor."""

    session: Any
    strict_updates: bool = True

    def execute_write_plan(
        self,
        plan: WritePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        execute_write_plan(
            self.session,
            plan,
            mapper_registry=mapper_registry,
            strict_updates=self.strict_updates,
        )

    def execute_delete_plan(
        self,
        plan: DeletePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        execute_delete_plan(self.session, plan, mapper_registry=mapper_registry)


@dataclass
class AsyncPlanExecutor:
    """Default async plan executor."""

    session: AsyncSession
    strict_updates: bool = True

    async def execute_write_plan(
        self,
        plan: WritePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        await async_execute_write_plan(
            self.session,
            plan,
            mapper_registry=mapper_registry,
            strict_updates=self.strict_updates,
        )

    async def execute_delete_plan(
        self,
        plan: DeletePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        await async_execute_delete_plan(self.session, plan, mapper_registry=mapper_registry)


@dataclass
class SyncSessionBackend:
    """SQLAlchemy sync session backend."""

    session: Any
    executor: PlanExecutor
    mapper_registry: Any | None = None

    def run_select(self, statement: Select[Any]) -> list[Any]:
        return list(self.session.exec(statement).all())

    def execute_write_plan(
        self,
        plan: WritePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        self.executor.execute_write_plan(
            plan, mapper_registry=mapper_registry or self.mapper_registry
        )

    def execute_delete_plan(
        self,
        plan: DeletePlan,
        *,
        mapper_registry: Any | None = None,
    ) -> None:
        self.executor.execute_delete_plan(
            plan, mapper_registry=mapper_registry or self.mapper_registry
        )

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
