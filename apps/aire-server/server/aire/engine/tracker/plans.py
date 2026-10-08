"""The rules about who may mutate what, and when — the state machine itself.

Its shape, and why it differs from the fi-core original it was vendored from,
are documented in this package's `__init__`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import replace

from .errors import (DependencyUnmet, PlanAlreadyTerminal, PlanNotFound,
                     StepAlreadyTerminal, StepIndexInvalid)
from .models import (TERMINAL_PLAN_STATES, TERMINAL_STEP_STATES, Plan,
                     PlanStatus, Step, StepStatus, settled_status)
from .reshape import insert_step, replace_tail
from .specs import build_steps


class TaskTracker:
    """The plans of ONE session. Every mutation replaces the frozen Plan."""

    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}
        self._starts: dict[str, dict[int, float]] = {}

    def get(self, plan_id: str) -> Plan:
        try:
            return self._plans[plan_id]
        except KeyError as exc:
            raise PlanNotFound(plan_id) from exc

    def declare(self, steps: list) -> Plan:
        """Register a plan. An empty checklist is refused: zero rows is a UI bug,
        never a useful state."""
        if not steps:
            raise ValueError("steps must not be empty")
        plan = Plan(plan_id=uuid.uuid4().hex[:16], steps=tuple(build_steps(steps)))
        self._plans[plan.plan_id] = plan
        self._starts[plan.plan_id] = {}
        return plan

    def start(self, plan_id: str, index: int) -> Step:
        """Mark a step RUNNING. Idempotent — a second call does not reset its
        clock. Refuses a settled step, and a step whose dependencies are open."""
        plan = self.get(plan_id)
        current = self._live_step(plan, index)
        if current.status is StepStatus.RUNNING:
            return current
        for dep in current.depends_on:
            if plan.steps[dep].status is not StepStatus.DONE:
                raise DependencyUnmet(f"step {index} depends on step {dep}, which is "
                                      f"{plan.steps[dep].status.value}, not done")
        self._starts[plan_id][index] = time.monotonic()
        return self._put(plan, index, replace(current, status=StepStatus.RUNNING),
                         PlanStatus.RUNNING)

    def end(self, plan_id: str, index: int, status: StepStatus,
            summary: str = "", error: str = "") -> Step:
        """Settle a step DONE / FAILED / CANCELLED, timing it when it was started.
        A model that skipped `start` leaves `duration_ms` null rather than
        inheriting a fabricated one."""
        plan = self.get(plan_id)
        current = self._live_step(plan, index)
        t0 = self._starts.get(plan_id, {}).get(index)
        step = replace(current, status=status, summary=summary, error=error,
                       duration_ms=None if t0 is None else int((time.monotonic() - t0) * 1000))
        after = tuple(step if i == index else s for i, s in enumerate(plan.steps))
        settled = all(s.status in TERMINAL_STEP_STATES for s in after)
        return self._put(plan, index, step,
                         settled_status(after) if settled else PlanStatus.RUNNING)

    def note(self, plan_id: str, index: int, note: str) -> Step:
        """Append progress to a live step. Append-only: a note never overwrites a
        summary, and a settled step takes none."""
        plan = self.get(plan_id)
        current = self._live_step(plan, index)
        if not note:
            return current
        step = replace(current, notes=current.notes + (note,))
        return self._put(plan, index, step, plan.status)

    def insert(self, plan_id: str, after_index: int, spec) -> Plan:
        """Insert a PENDING step after `after_index` (-1 prepends)."""
        plan = self._open_plan(plan_id)
        if after_index < -1 or after_index >= plan.step_count:
            raise StepIndexInvalid(f"after_index {after_index} is outside plan {plan_id}")
        return self._save(insert_step(plan, after_index, spec))

    def replan(self, plan_id: str, from_index: int, new_steps: list) -> Plan:
        """Replace everything from `from_index` on, and drop the timings of the
        steps that stopped existing — a clock kept for a removed step would later
        stamp a duration onto whatever step inherited its index."""
        if not new_steps:
            raise ValueError("new_steps must not be empty")
        plan = self._open_plan(plan_id)
        if from_index < 0 or from_index > plan.step_count:
            raise StepIndexInvalid(f"from_index {from_index} is outside plan {plan_id}")
        reshaped, kept = replace_tail(plan, from_index, new_steps)
        self._starts[plan_id] = {k: v for k, v in self._starts.get(plan_id, {}).items()
                                 if k < len(kept)}
        return self._save(reshaped)

    def cancel(self, plan_id: str, reason: str = "") -> Plan:
        """Cancel the whole plan. Idempotent when already cancelled; refused on a
        plan that already completed or failed — those settled, they did not stop."""
        plan = self.get(plan_id)
        if plan.status is PlanStatus.CANCELLED:
            return plan
        if plan.status in TERMINAL_PLAN_STATES:
            raise PlanAlreadyTerminal(f"plan {plan_id} is {plan.status.value}; it cannot be cancelled")
        steps = tuple(s if s.status in TERMINAL_STEP_STATES else
                      replace(s, status=StepStatus.CANCELLED, error=reason or s.error)
                      for s in plan.steps)
        return self._save(replace(plan, steps=steps, status=PlanStatus.CANCELLED))

    def finalize(self, plan_id: str) -> Plan:
        """Settle the plan: whatever never ran is SKIPPED, and the outcome follows
        from the steps. Idempotent."""
        plan = self.get(plan_id)
        if plan.status in TERMINAL_PLAN_STATES:
            return plan
        steps = tuple(replace(s, status=StepStatus.SKIPPED)
                      if s.status in (StepStatus.PENDING, StepStatus.RUNNING) else s
                      for s in plan.steps)
        return self._save(replace(plan, steps=steps, status=settled_status(steps)))

    def _open_plan(self, plan_id: str) -> Plan:
        plan = self.get(plan_id)
        if plan.status in TERMINAL_PLAN_STATES:
            raise PlanAlreadyTerminal(f"plan {plan_id} is {plan.status.value}; it cannot be reshaped")
        return plan

    def _live_step(self, plan: Plan, index: int) -> Step:
        if not 0 <= index < plan.step_count:
            raise StepIndexInvalid(f"step {index} is outside plan {plan.plan_id}")
        step = plan.steps[index]
        if step.status in TERMINAL_STEP_STATES:
            raise StepAlreadyTerminal(f"step {index} is already {step.status.value}")
        return step

    def _put(self, plan: Plan, index: int, step: Step, status: PlanStatus) -> Step:
        steps = tuple(step if i == index else s for i, s in enumerate(plan.steps))
        self._save(replace(plan, steps=steps, status=status))
        return step

    def _save(self, plan: Plan) -> Plan:
        self._plans[plan.plan_id] = plan  # the one writer — every path lands here
        return plan
