"""TaskTracker — in-memory plan/step state, scoped by session.

The tracker holds the live plans for every session that the agent has
declared. Operations are SYNCHRONOUS (in-memory dict mutations) — the MCP
server wraps them in async tool handlers, but the tracker itself is dep-free
and unit-testable without any SDK.

Why in-memory? A plan lives for one turn (seconds). The runner reads its
state to emit stream events; once the turn ends, the plan can be garbage-
collected — there is no value in persisting a finished plan beyond the
client's transcript. Multi-replica deploys: scope by ``session_id`` and a
sticky load-balancer routes the same session to the same replica; the
tracker is process-local same as the conversation store's in-memory variant.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import replace

from .models import Plan, PlanStatus, Step, StepStatus


class PlanNotFound(KeyError):
    """Raised when an operation references a ``plan_id`` the tracker doesn't
    know — typically the agent passed a stale id, or a different session."""


class StepIndexInvalid(IndexError):
    """Raised when ``step_index`` is outside the declared range. Catching
    this on the MCP boundary lets the server return a structured error instead
    of an opaque traceback."""


class TaskTracker:
    """Per-session in-memory plan registry.

    Public API mirrors the MCP tools 1:1 so the server stays a thin adapter:

      - :meth:`declare_plan(session_id, steps)` → :class:`Plan`
      - :meth:`start_step(plan_id, step_index)` → :class:`Step`
      - :meth:`complete_step(plan_id, step_index, summary)` → :class:`Step`
      - :meth:`fail_step(plan_id, step_index, error)` → :class:`Step`

    Plan/step mutations replace the immutable dataclass via :func:`replace`
    and re-insert into the tracker's dict, so callers that hold a previous
    reference don't see partial mutations."""

    def __init__(self) -> None:
        # plan_id -> Plan. Sessions cross-reference plans via session_id on the
        # Plan itself — simpler than a nested dict and fine for the volumes we
        # see (one plan per turn, kept transient).
        self._plans: dict[str, Plan] = {}
        # plan_id -> step_index -> monotonic start time. Used to fill
        # duration_ms on complete_step / fail_step. Kept separate from the
        # frozen Plan so the lifecycle stays immutable.
        self._step_starts: dict[str, dict[int, float]] = {}

    # --- queries ----------------------------------------------------------

    def get(self, plan_id: str) -> Plan:
        """Return the plan, or raise :class:`PlanNotFound`."""
        try:
            return self._plans[plan_id]
        except KeyError as e:
            raise PlanNotFound(plan_id) from e

    def list_for_session(self, session_id: str) -> list[Plan]:
        """Every plan recorded for one session, in declaration order."""
        return [p for p in self._plans.values() if p.session_id == session_id]

    # --- mutations --------------------------------------------------------

    def declare_plan(self, session_id: str, steps: list[str]) -> Plan:
        """Register a new plan with PENDING steps, return the live Plan.

        Empty ``steps`` is allowed (degenerate plan — useful for "I have
        nothing to do" responses) but rare; the MCP server may reject it
        at the boundary depending on the consumer's policy."""
        plan_id = uuid.uuid4().hex[:12]
        step_objs = tuple(Step(index=i, label=label) for i, label in enumerate(steps))
        plan = Plan(plan_id=plan_id, session_id=session_id, status=PlanStatus.DECLARED, steps=step_objs)
        self._plans[plan_id] = plan
        self._step_starts[plan_id] = {}
        return plan

    def start_step(self, plan_id: str, step_index: int) -> Step:
        """Mark a step RUNNING. The plan flips to RUNNING on the first call."""
        plan = self.get(plan_id)
        self._check_index(plan, step_index)
        self._step_starts[plan_id][step_index] = time.monotonic()
        step = replace(plan.steps[step_index], status=StepStatus.RUNNING)
        return self._replace_step(plan, step_index, step, plan_status=PlanStatus.RUNNING)

    def complete_step(self, plan_id: str, step_index: int, summary: str = "") -> Step:
        """Mark a step DONE with measured ``duration_ms``. Plan flips to
        COMPLETED only when every step is DONE/SKIPPED/FAILED."""
        return self._end_step(plan_id, step_index, StepStatus.DONE, summary=summary)

    def fail_step(self, plan_id: str, step_index: int, error: str = "") -> Step:
        """Mark a step FAILED. The plan goes to FAILED overall — a plan with
        a failed step is failed, regardless of what comes after."""
        return self._end_step(plan_id, step_index, StepStatus.FAILED, error=error)

    # --- helpers ----------------------------------------------------------

    def _check_index(self, plan: Plan, step_index: int) -> None:
        if not (0 <= step_index < plan.step_count):
            raise StepIndexInvalid(
                f"step_index {step_index} out of range for plan {plan.plan_id} ({plan.step_count} steps)"
            )

    def _end_step(self, plan_id: str, step_index: int, status: StepStatus, *, summary: str = "", error: str = "") -> Step:
        plan = self.get(plan_id)
        self._check_index(plan, step_index)
        t0 = self._step_starts.get(plan_id, {}).get(step_index)
        # If the agent skipped start_step (some models do), we have no t0 —
        # leave duration_ms None rather than fabricating one.
        dur = int((time.monotonic() - t0) * 1000) if t0 is not None else None
        step = replace(plan.steps[step_index], status=status, duration_ms=dur, summary=summary, error=error)
        # Decide the plan's overall status from the new step set.
        new_steps = list(plan.steps)
        new_steps[step_index] = step
        any_failed = any(s.status is StepStatus.FAILED for s in new_steps)
        all_settled = all(s.status in (StepStatus.DONE, StepStatus.SKIPPED, StepStatus.FAILED) for s in new_steps)
        new_plan_status = PlanStatus.FAILED if any_failed and all_settled else (
            PlanStatus.COMPLETED if all_settled else PlanStatus.RUNNING
        )
        return self._replace_step(plan, step_index, step, plan_status=new_plan_status)

    def _replace_step(self, plan: Plan, step_index: int, step: Step, *, plan_status: PlanStatus) -> Step:
        new_steps = tuple(step if i == step_index else s for i, s in enumerate(plan.steps))
        self._plans[plan.plan_id] = replace(plan, steps=new_steps, status=plan_status)
        return step
