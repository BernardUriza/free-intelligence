"""The plan and its steps — immutable, and the vocabulary both halves share.

Vendored from fi-core's `task_tracker.models` (backlog #45), for the reason
decision #1 gives: fi-core is not on PyPI and the droplet must not depend on a
repo another agent edits. The shapes are kept name-for-name with upstream so a
consumer's event translator reads them unchanged.

Frozen on purpose: every mutation returns a NEW Plan via `dataclasses.replace`,
so a caller holding an earlier reference never observes a half-applied change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    DECLARED = "declared"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STEP_STATES = frozenset(
    {StepStatus.DONE, StepStatus.FAILED, StepStatus.CANCELLED, StepStatus.SKIPPED}
)
TERMINAL_PLAN_STATES = frozenset(
    {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED}
)


@dataclass(frozen=True)
class Step:
    index: int
    label: str
    status: StepStatus = StepStatus.PENDING
    duration_ms: int | None = None
    summary: str = ""
    error: str = ""
    active_form: str = ""
    depends_on: tuple[int, ...] = ()
    notes: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"index": self.index, "label": self.label, "status": self.status.value,
                "duration_ms": self.duration_ms, "summary": self.summary,
                "error": self.error, "notes": list(self.notes)}


@dataclass(frozen=True)
class Plan:
    plan_id: str
    status: PlanStatus = PlanStatus.DECLARED
    steps: tuple[Step, ...] = field(default_factory=tuple)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def as_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "status": self.status.value,
                "steps": [s.as_dict() for s in self.steps]}


def settled_status(steps: tuple[Step, ...]) -> PlanStatus:
    """What a plan IS once every step has stopped moving.

    Failure outranks cancellation, and cancellation only wins when nothing
    succeeded: a plan with one done step and one cancelled step COMPLETED — it
    did not get cancelled. Here rather than in the tracker because it reads only
    these shapes and decides nothing about who may mutate them."""
    if any(s.status is StepStatus.FAILED for s in steps):
        return PlanStatus.FAILED
    cancelled = any(s.status is StepStatus.CANCELLED for s in steps)
    if cancelled and not any(s.status is StepStatus.DONE for s in steps):
        return PlanStatus.CANCELLED
    return PlanStatus.COMPLETED
