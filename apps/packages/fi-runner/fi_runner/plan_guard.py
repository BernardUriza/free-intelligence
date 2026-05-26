"""PlanGuard — pre-execution review of an agent's declared plan.

The promise of plan-first chain-of-thought (see
:mod:`fi_core.task_tracker`) is that an agent must *write down* its plan
BEFORE acting. That commitment is what lets us reject prohibited plans
*before* any tool runs — moving the anti-drift defense from post-hoc text
sanitization (an :class:`AntiDriftGuard`-style retry loop) UP to
pre-execution review (this module).

A PlanGuard is fundamentally different from a :class:`Guard` in
:mod:`fi_runner.guards`:

  - A :class:`Guard` inspects the **response text** AFTER the turn settles.
  - A :class:`PlanGuard` inspects the **declared plan steps** BEFORE the
    agent calls any other tool, from the ``plan`` stream event surfaced by
    :func:`fi_runner.runner._derive_plan_events`.

A guard's reaction is bounded: it can mark the plan as ``rejected`` (with a
reason and the matched patterns), and the caller — fi-runner or a custom
turn loop — decides what to do with that signal:

  - Emit a ``plan_rejected`` stream event so the UI shows "Plan blocked".
  - Issue ``mcp__fi_core_task_tracker__cancel_plan`` to settle the tracker.
  - Inject a reinforcement and retry the turn (handled by the caller's
    retry policy, mirroring the :class:`AntiDriftGuard` flow).

Determinism is the point: a PlanGuard uses regex patterns and label
predicates, never the LLM. A guard MUST be safe to call thousands of
times per second without external dependencies. Build via :func:`plan_guard`
(simple regex policy) or instantiate :class:`PlanGuard` directly for a
fully custom predicate."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


# A step spec, as it crosses the stream event boundary, is either:
#   - a plain string label, or
#   - a dict with at least a "label" key (plus optional active_form/depends_on/metadata).
# We accept both transparently — the guard inspects the label text.
PlanStepSpec = str | dict[str, Any]


@dataclass(frozen=True)
class PlanGuardOutcome:
    """The result of inspecting a declared plan.

    ``allowed`` — True when no policy violation was found. ``matched`` — the
    list of step indexes that violated the policy, alongside the offending
    text and pattern name. ``reason`` — a short human-readable summary for
    the UI / ``plan_rejected`` event. ``reinforcement`` — optional system
    prompt addendum a caller may inject before retrying the turn.

    The outcome is intentionally compact and JSON-serializable so the runner
    can put it on the stream event verbatim."""

    allowed: bool
    matched: tuple[dict[str, Any], ...] = ()
    reason: str = ""
    reinforcement: str = ""


@dataclass
class PlanGuard:
    """Pre-execution plan inspector.

    ``predicate`` decides per-step whether the step is allowed. Default
    implementation is a regex blocklist (``blocked_patterns``) — any pattern
    that matches the step's label (case-insensitive by default) blocks the
    plan. ``name`` is the guard identifier; ``reinforcement`` is what the
    caller may append to the system prompt on retry.

    A custom predicate gets ``(step_index, label, full_spec)`` and returns
    ``(allowed, matched_dict_or_None)`` — letting consumers express richer
    policies (e.g. "deny if metadata.tool starts with 'admin_'")."""

    blocked_patterns: list[re.Pattern[str]] = field(default_factory=list)
    predicate: Callable[[int, str, dict[str, Any] | str], tuple[bool, dict[str, Any] | None]] | None = None
    reinforcement: str = ""
    name: str = "plan_guard"

    def inspect(self, steps: Iterable[PlanStepSpec]) -> PlanGuardOutcome:
        """Inspect the declared plan, return the outcome.

        If a custom ``predicate`` is set it is used per-step; otherwise the
        default regex blocklist is applied. A plan is allowed iff EVERY step
        is allowed."""
        matched: list[dict[str, Any]] = []
        for idx, spec in enumerate(steps):
            label = self._label_of(spec)
            if self.predicate is not None:
                ok, hit = self.predicate(idx, label, spec)
                if not ok and hit is not None:
                    matched.append({"index": idx, "label": label, **hit})
            else:
                hit = self._default_violation(label)
                if hit is not None:
                    matched.append({"index": idx, "label": label, **hit})
        if not matched:
            return PlanGuardOutcome(allowed=True)
        reason = (
            f"plan rejected: {len(matched)} step(s) match a blocked pattern "
            f"({', '.join(m.get('pattern', '?') for m in matched)})"
        )
        return PlanGuardOutcome(
            allowed=False,
            matched=tuple(matched),
            reason=reason,
            reinforcement=self.reinforcement,
        )

    def _label_of(self, spec: PlanStepSpec) -> str:
        if isinstance(spec, str):
            return spec
        if isinstance(spec, dict):
            return str(spec.get("label", ""))
        return str(spec)

    def _default_violation(self, label: str) -> dict[str, Any] | None:
        for p in self.blocked_patterns:
            if p.search(label):
                return {"pattern": p.pattern, "matched_text": label}
        return None


def plan_guard(
    *,
    blocked_patterns: Iterable[str | re.Pattern[str]] = (),
    reinforcement: str = "",
    name: str = "plan_guard",
    flags: int = re.IGNORECASE,
) -> PlanGuard:
    """Build a :class:`PlanGuard` from a regex blocklist.

    ``blocked_patterns`` accepts raw strings (compiled with ``flags``) or
    pre-compiled patterns. Empty patterns list yields a guard that allows
    every plan — useful as a default that a consumer can extend without
    branching on ``None``."""
    compiled: list[re.Pattern[str]] = []
    for p in blocked_patterns:
        if isinstance(p, re.Pattern):
            compiled.append(p)
        else:
            compiled.append(re.compile(p, flags))
    return PlanGuard(
        blocked_patterns=compiled,
        reinforcement=reinforcement,
        name=name,
    )


__all__ = [
    "PlanGuard",
    "PlanGuardOutcome",
    "PlanStepSpec",
    "plan_guard",
]
