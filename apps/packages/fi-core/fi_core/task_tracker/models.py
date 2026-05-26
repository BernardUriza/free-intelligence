"""Domain types for the task tracker — :class:`Plan` and :class:`Step`.

Frozen dataclasses so a Plan/Step in flight is immutable; the tracker swaps
references through :func:`dataclasses.replace`. Status enums use string values
so they survive JSON serialization without a custom encoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepStatus(str, Enum):
    """Lifecycle of one plan step.

    ``PENDING`` — declared, not started. ``RUNNING`` — start_step was called.
    ``DONE`` — complete_step. ``FAILED`` — fail_step. ``SKIPPED`` — the plan
    finished without this step being run (e.g. early return). String values
    keep them JSON-serializable for the wire."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    """Lifecycle of a whole plan.

    ``DECLARED`` — declare_plan called, no step started yet. ``RUNNING`` — at
    least one step started. ``COMPLETED`` — all steps reached DONE/SKIPPED.
    ``FAILED`` — any step ended FAILED (a plan with one failed step is failed
    overall even if others succeeded — partial success isn't a plan outcome)."""

    DECLARED = "declared"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Step:
    """One step in a plan. ``index`` is the position in the declared list
    (0-based, matches what the agent passes to start_step/complete_step).

    ``duration_ms`` is None until ``complete_step`` / ``fail_step``. ``summary``
    is the optional text the agent wrote when finishing a step — propagates as
    the next step's context in the UI checklist."""

    index: int
    label: str
    status: StepStatus = StepStatus.PENDING
    duration_ms: int | None = None
    summary: str = ""
    error: str = ""


@dataclass(frozen=True)
class Plan:
    """A declared plan: ordered list of steps under one ``plan_id`` for a
    session. ``session_id`` lets the tracker scope plans per conversation
    (in a shared in-memory tracker, one session's plans don't see another's)."""

    plan_id: str
    session_id: str
    status: PlanStatus = PlanStatus.DECLARED
    steps: tuple[Step, ...] = field(default_factory=tuple)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def completed_count(self) -> int:
        return sum(1 for s in self.steps if s.status in (StepStatus.DONE, StepStatus.SKIPPED))

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.steps if s.status is StepStatus.FAILED)
