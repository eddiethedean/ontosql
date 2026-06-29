"""Pending write/delete unit-of-work queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ontosql.compile.plan import DeletePlan, WritePlan
from ontosql.semantic.model import OntoModel


@dataclass
class PendingDelete:
    """Queued delete plan with instance retained for deferred graph sync."""

    plan: DeletePlan
    instance: OntoModel
    snapshot: dict[str, Any] | None = None


@dataclass
class PendingWorkQueue:
    """Deferred save/delete plans."""

    pending: list[WritePlan | PendingDelete] = field(default_factory=list)
    pending_instances: dict[int, OntoModel] = field(default_factory=dict)
    pending_insert_objects: set[int] = field(default_factory=set)
    pending_prior_nested: dict[int, frozenset[str]] = field(default_factory=dict)
    # Plans whose SQL already ran but post-SQL flush steps may need retry (partial flush).
    pending_sql_results: dict[int, Any] = field(default_factory=dict)
    pending_delete_sql_applied: set[int] = field(default_factory=set)

    def queue_pending_write(
        self,
        plan: WritePlan,
        instance: OntoModel,
        *,
        prior_nested_iris: frozenset[str] | None = None,
    ) -> None:
        obj_id = id(instance)
        entity_type = type(instance)
        identity = getattr(instance, entity_type.identity_field, None)
        if obj_id in self.pending_insert_objects:
            for idx, item in enumerate(self.pending):
                if isinstance(item, WritePlan) and self.pending_instances.get(id(item)) is instance:
                    old_plan_id = id(item)
                    self.pending[idx] = plan
                    self.pending_instances.pop(old_plan_id, None)
                    self.pending_instances[id(plan)] = instance
                    self.pending_prior_nested.pop(old_plan_id, None)
                    self._migrate_sql_result(old_plan_id, id(plan))
                    if prior_nested_iris is not None:
                        self.pending_prior_nested[id(plan)] = prior_nested_iris
                    return
        if identity is not None:
            for idx, item in enumerate(self.pending):
                if not isinstance(item, WritePlan):
                    continue
                other = self.pending_instances.get(id(item))
                if other is None:
                    continue
                other_id = getattr(other, other.identity_field, None)
                if other_id == identity and type(other) is entity_type:
                    old_plan_id = id(item)
                    self.pending[idx] = plan
                    self.pending_instances.pop(old_plan_id, None)
                    self.pending_instances[id(plan)] = instance
                    self.pending_prior_nested.pop(old_plan_id, None)
                    self._migrate_sql_result(old_plan_id, id(plan))
                    self.pending_insert_objects.discard(id(other))
                    self.pending_insert_objects.add(obj_id)
                    if prior_nested_iris is not None:
                        self.pending_prior_nested[id(plan)] = prior_nested_iris
                    return
        self.pending_insert_objects.add(obj_id)
        self.pending.append(plan)
        self.pending_instances[id(plan)] = instance
        if prior_nested_iris is not None:
            self.pending_prior_nested[id(plan)] = prior_nested_iris

    def prior_nested_for_plan(self, plan: WritePlan) -> frozenset[str] | None:
        return self.pending_prior_nested.get(id(plan))

    def peek_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        return self.pending_instances.get(id(plan))

    def pop_pending_instance(self, plan: WritePlan) -> OntoModel | None:
        instance = self.pending_instances.pop(id(plan), None)
        if instance is not None:
            self.pending_insert_objects.discard(id(instance))
        return instance

    def _migrate_sql_result(self, old_plan_id: int, new_plan_id: int) -> None:
        if old_plan_id in self.pending_sql_results:
            self.pending_sql_results[new_plan_id] = self.pending_sql_results.pop(old_plan_id)

    def sql_result_for_plan(self, plan: WritePlan) -> Any | None:
        return self.pending_sql_results.get(id(plan))

    def mark_sql_applied(self, plan: WritePlan, inserted_id: Any) -> None:
        self.pending_sql_results[id(plan)] = inserted_id

    def clear_sql_applied(self, plan: WritePlan) -> None:
        self.pending_sql_results.pop(id(plan), None)

    def is_delete_sql_applied(self, pending: PendingDelete) -> bool:
        return id(pending) in self.pending_delete_sql_applied

    def mark_delete_sql_applied(self, pending: PendingDelete) -> None:
        self.pending_delete_sql_applied.add(id(pending))

    def clear_delete_sql_applied(self, pending: PendingDelete) -> None:
        self.pending_delete_sql_applied.discard(id(pending))

    def clear(self) -> None:
        self.pending.clear()
        self.pending_instances.clear()
        self.pending_insert_objects.clear()
        self.pending_prior_nested.clear()
        self.pending_sql_results.clear()
        self.pending_delete_sql_applied.clear()

    def clear_after_flush(self) -> None:
        self.pending.clear()
        self.pending_instances.clear()
        self.pending_insert_objects.clear()
        self.pending_prior_nested.clear()
        self.pending_sql_results.clear()
        self.pending_delete_sql_applied.clear()
