"""How a plan's SHAPE changes — pure functions, `Plan` in and `Plan` out.

Separate from the state machine because the two never touch the same field:
reshaping moves steps around and renumbers them, and never reads or writes a
step's status or its clock. Keeping the shape math here leaves the tracker as
what it is — the rules about who may mutate what, and when.

Both refuse to invent an ordering: a dependency may only ever point backwards,
so a reshape that would leave one pointing forward raises instead of repairing.
"""

from __future__ import annotations

from dataclasses import replace

from .errors import StepAlreadyTerminal
from .models import TERMINAL_STEP_STATES, Plan, Step
from .specs import build_step, build_steps


def insert_step(plan: Plan, after_index: int, spec) -> Plan:
    """A PENDING step after `after_index` (-1 prepends). Later steps are
    renumbered, and every `depends_on` that crossed the seam moves with them —
    otherwise an insert would silently repoint a dependency at a new neighbour."""
    at = after_index + 1
    shifted = [s if s.index < at else
               replace(s, index=s.index + 1,
                       depends_on=tuple(d + 1 if d >= at else d for d in s.depends_on))
               for s in plan.steps]
    steps = tuple(sorted([*shifted, build_step(at, spec)], key=lambda s: s.index))
    return replace(plan, steps=steps)


def replace_tail(plan: Plan, from_index: int, new_steps: list) -> tuple[Plan, list[Step]]:
    """Everything from `from_index` on, replaced. Returns the new plan and the
    steps that were KEPT, so the caller can drop the timings of what it dropped.

    What came before must already be settled: replanning around a step that is
    still running would leave a clock ticking on a step that no longer exists."""
    kept = list(plan.steps[:from_index])
    for s in kept:
        if s.status not in TERMINAL_STEP_STATES:
            raise StepAlreadyTerminal(f"cannot replan past step {s.index}: it is {s.status.value}")
    fresh = build_steps(new_steps, from_index)
    return replace(plan, steps=tuple([*kept, *fresh])), kept
