"""A step spec arrives as arbitrary JSON — this is where it stops being that.

Separate from the state machine because it is a different job: the tracker
decides what a plan may DO, this decides what the wire may SAY. Every spec the
model sends crosses an MCP boundary, so it is untrusted shape, validated here
once and never trusted again downstream.
"""

from __future__ import annotations

from typing import Any

from .models import Step


def build_step(index: int, spec: Any) -> Step:
    """A Step from a label string or a `{label, active_form, depends_on, metadata}`
    dict. Raises ValueError with the offending index — the adapter hands that
    text back to the model, which is the only party that can fix it."""
    if isinstance(spec, str):
        if not spec:
            raise ValueError(f"step {index} has an empty label")
        return Step(index=index, label=spec)
    if not isinstance(spec, dict):
        raise ValueError(f"step {index} must be a string or an object, got {type(spec).__name__}")
    label = spec.get("label")
    if not isinstance(label, str) or not label:
        raise ValueError(f"step {index} is missing its required 'label' string")
    return Step(index=index, label=label,
                active_form=spec.get("active_form", "") or "",
                depends_on=tuple(spec.get("depends_on") or ()),
                metadata=spec.get("metadata") or None)


def check_backward_deps(step: Step) -> None:
    """A step may only depend on EARLIER steps. That single rule forbids cycles
    structurally, with no DAG validator to write or to get wrong."""
    for dep in step.depends_on:
        if not isinstance(dep, int) or dep < 0 or dep >= step.index:
            raise ValueError(
                f"step {step.index} depends on {dep!r}; it must reference an earlier step"
            )


def build_steps(specs: list, start_index: int = 0) -> list[Step]:
    """A whole run of steps, each validated and each checked to depend only on
    an earlier one. `declare` and `replan` both build a run; sharing the loop is
    what keeps a rule from being enforced on one path and forgotten on the other."""
    out = []
    for offset, raw in enumerate(specs):
        step = build_step(start_index + offset, raw)
        check_backward_deps(step)
        out.append(step)
    return out
