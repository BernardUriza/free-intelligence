"""Domain types for the task tracker — :class:`Plan` and :class:`Step`.

Frozen dataclasses so a Plan/Step in flight is immutable; the tracker swaps
references through :func:`dataclasses.replace`. Status enums use string values
so they survive JSON serialization without a custom encoder.

The :class:`Step` carries everything a UI needs to paint a rich checklist
row: ``active_form`` for the in-progress verb phrase, ``depends_on`` to model
a small DAG when steps can run in parallel, ``notes`` for incremental progress
text accumulated during a long step, ``metadata`` as an escape-hatch for
consumer-specific data. Terminal states (DONE/FAILED/SKIPPED/CANCELLED) are
INMUTABLE — :data:`TERMINAL_STEP_STATES` is the canonical set; the tracker
rejects any mutation that targets a step already in this set."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Lifecycle of one plan step.

    ``PENDING`` — declared, not started. ``RUNNING`` — start_step was called.
    ``DONE`` — complete_step. ``FAILED`` — fail_step. ``SKIPPED`` — the plan
    finished without this step being run (e.g. early return; the tracker
    auto-skips on :meth:`TaskTracker.finalize_plan`). ``CANCELLED`` — the
    client sent an MCP-style cancellation while the step was RUNNING.

    String values keep them JSON-serializable for the wire."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PlanStatus(str, Enum):
    """Lifecycle of a whole plan.

    ``DECLARED`` — declare_plan called, no step started yet. ``RUNNING`` — at
    least one step started. ``COMPLETED`` — every step settled to a successful
    terminal (DONE or SKIPPED). ``FAILED`` — any step settled to FAILED (the
    plan is failed overall even if others succeeded). ``CANCELLED`` — the plan
    was cancelled explicitly via :meth:`TaskTracker.cancel_plan` while still
    in flight; differs from FAILED because no step actually errored."""

    DECLARED = "declared"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


#: Steps in any of these states are TERMINAL — mutations raise.
TERMINAL_STEP_STATES = frozenset({
    StepStatus.DONE,
    StepStatus.FAILED,
    StepStatus.SKIPPED,
    StepStatus.CANCELLED,
})

#: Plans in any of these states are TERMINAL — mutations raise.
TERMINAL_PLAN_STATES = frozenset({
    PlanStatus.COMPLETED,
    PlanStatus.FAILED,
    PlanStatus.CANCELLED,
})


@dataclass(frozen=True)
class Step:
    """One step in a plan. ``index`` is the position in the declared list
    (0-based, matches what the agent passes to start_step/complete_step).

    ``label`` is the static name shown when the step is PENDING or DONE.
    ``active_form`` is the verb-phrase shown while RUNNING (e.g. ``"Searching
    SERP for acme.com"`` instead of the noun-phrase label ``"Search SERP"``).
    Mirrors Anthropic's Task tool ``activeForm`` field — better UX in the
    checklist when an icon is spinning next to the row.

    ``duration_ms`` is None until ``complete_step`` / ``fail_step``.
    ``summary`` is the one-line outcome the agent wrote at the end.
    ``notes`` accumulate intermediate context written via ``note_step``
    during a long-running step — never overwritten, append-only.

    ``depends_on`` is a tuple of indexes this step requires DONE first.
    Empty tuple means "no deps; start whenever". A small DAG, not a full
    graph engine — agents who don't care can just use a flat list and the
    tracker treats it as a linear plan.

    ``metadata`` is a per-step opaque escape hatch for consumer-specific
    data (e.g. expected latency, external task_id). Pass at declare time;
    the tracker preserves it as-is and never inspects it."""

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


@dataclass(frozen=True)
class Plan:
    """A declared plan: ordered list of steps under one ``plan_id`` for a
    session. ``session_id`` lets the tracker scope plans per conversation
    (in a shared in-memory tracker, one session's plans don't see another's).

    ``plan_id`` is a 64-bit hex truncation of UUIDv4 — enough entropy to
    avoid collisions inside a single process for the realistic lifetime of
    the in-memory tracker (TTL-evicted)."""

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

    @property
    def cancelled_count(self) -> int:
        return sum(1 for s in self.steps if s.status is StepStatus.CANCELLED)

    @property
    def is_terminal(self) -> bool:
        """True if the plan reached COMPLETED/FAILED/CANCELLED. Callers use
        this to know whether emitting a final ``plan_completed`` / ``plan_failed``
        / ``plan_cancelled`` event is appropriate."""
        return self.status in TERMINAL_PLAN_STATES
