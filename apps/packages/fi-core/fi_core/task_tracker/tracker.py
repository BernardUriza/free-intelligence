"""TaskTracker — in-memory plan/step state, scoped by session.

The tracker holds the live plans for every session that the agent has
declared. Operations are SYNCHRONOUS (in-memory dict mutations) — the MCP
server wraps them in async tool handlers, but the tracker itself is dep-free
and unit-testable without any SDK.

In-memory but bounded: plans are kept in a TTL-aware dict so a session that
crashes between :meth:`start_step` and :meth:`complete_step` doesn't leak a
plan forever. The TTL is generous (1h by default) because a plan lives for
seconds; an entry that's still around at TTL eviction was always orphaned.

Concurrency model: SINGLE-EVENT-LOOP by design. The FastMCP stdio transport
runs one event loop per server process; each tool handler is sync (no
``await`` inside the tracker mutations), so the event loop never preempts
between checking and writing state. **No lock is used** — a ``threading.RLock``
would be false advertising under asyncio (single-thread + reentrant = the
critical section is NOT actually protected from concurrent coroutines that
``await`` mid-mutation). If a future variant needs concurrency safety
(HTTP/SSE multi-replica or async tracker methods), swap this implementation
for one backed by ``asyncio.Lock`` AND make the methods async, OR use a
Redis-backed store with optimistic concurrency. Don't try to bolt a thread
lock onto async code — it's the canonical anti-pattern.

Multi-replica deploys: scope by ``session_id`` and a sticky load-balancer
routes the same session to the same replica; the tracker is process-local
same as the conversation store's in-memory variant. A Redis-backed variant
is straightforward but unnecessary while a plan's lifetime is one turn.
"""

from __future__ import annotations

import time
import uuid
from contextlib import nullcontext
from dataclasses import replace
from typing import Any

from .models import (
    Plan,
    PlanStatus,
    Step,
    StepStatus,
    TERMINAL_PLAN_STATES,
    TERMINAL_STEP_STATES,
)


class PlanNotFound(KeyError):
    """Raised when an operation references a ``plan_id`` the tracker doesn't
    know — typically the agent passed a stale id, or a different session."""


class StepIndexInvalid(IndexError):
    """Raised when ``step_index`` is outside the declared range. Catching
    this on the MCP boundary lets the server return a structured error instead
    of an opaque traceback."""


class StepAlreadyTerminal(RuntimeError):
    """Raised when a mutation targets a step already in DONE/FAILED/SKIPPED/
    CANCELLED. Terminal states are inmutable — append-only semantics so a
    late retry from the network can't regress state."""


class PlanAlreadyTerminal(RuntimeError):
    """Raised when a mutation targets a plan already in
    COMPLETED/FAILED/CANCELLED — same append-only guarantee at plan scope."""


class DependencyUnmet(RuntimeError):
    """Raised when ``start_step`` is called on a step whose ``depends_on``
    list contains a step that isn't DONE yet. Lets the agent express a small
    DAG; the tracker refuses to start a step out of order."""


class SessionMismatch(PermissionError):
    """Raised when a caller queries or mutates a plan that belongs to a
    different ``session_id``. Plan IDs are sensitive capability handles in
    a multi-tenant runtime; cross-session access is rejected."""


# 1h: a plan lives for seconds. If it's still here at 1h, it's orphaned and
# we want it gone before it costs more RAM than a polite cleanup pass.
_DEFAULT_TTL_SECONDS = 3600


class _TTLStore:
    """Tiny TTL-evicting dict — purges on every mutation and on get-miss.

    No background thread (a per-process MCP server doesn't need one) and no
    LRU bound — the eviction is purely time-based, which matches the
    "plan-lives-for-one-turn" lifecycle. Built in-tree to keep fi-core
    dep-free; if we ever need LFU or maxsize, swap for ``cachetools.TTLCache``
    (same surface)."""

    def __init__(self, *, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _purge_expired(self) -> None:
        now = self._now()
        expired = [k for k, t in self._timestamps.items() if (now - t) > self._ttl]
        for k in expired:
            self._data.pop(k, None)
            self._timestamps.pop(k, None)

    def __setitem__(self, key: str, value: Any) -> None:
        self._purge_expired()
        self._data[key] = value
        self._timestamps[key] = self._now()

    def __getitem__(self, key: str) -> Any:
        # Purge before lookup so a stale entry doesn't satisfy a read.
        self._purge_expired()
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        self._purge_expired()
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        self._purge_expired()
        return self._data.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        self._purge_expired()
        self._timestamps.pop(key, None)
        return self._data.pop(key, default)

    def values(self):
        self._purge_expired()
        return self._data.values()

    def items(self):
        self._purge_expired()
        return self._data.items()

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._data)


class TaskTracker:
    """Per-session in-memory plan registry with TTL eviction.

    Public API mirrors the MCP tools 1:1 so the server stays a thin adapter:

      - :meth:`declare_plan(session_id, steps)` → :class:`Plan`
      - :meth:`start_step(plan_id, step_index, session_id)` → :class:`Step`
      - :meth:`complete_step(plan_id, step_index, summary, session_id)` → :class:`Step`
      - :meth:`fail_step(plan_id, step_index, error, session_id)` → :class:`Step`
      - :meth:`cancel_step(plan_id, step_index, reason, session_id)` → :class:`Step`
      - :meth:`note_step(plan_id, step_index, note, session_id)` → :class:`Step`
      - :meth:`insert_step(plan_id, after_index, step_spec, session_id)` → :class:`Plan`
      - :meth:`replan(plan_id, from_index, new_steps, session_id)` → :class:`Plan`
      - :meth:`cancel_plan(plan_id, reason, session_id)` → :class:`Plan`
      - :meth:`finalize_plan(plan_id, session_id)` → :class:`Plan`
      - :meth:`list_plans(session_id)` → list[:class:`Plan`]

    Plan/step mutations replace the immutable dataclass via :func:`replace`
    and re-insert into the tracker's dict, so callers that hold a previous
    reference don't see partial mutations."""

    def __init__(self, *, ttl_seconds: float = _DEFAULT_TTL_SECONDS) -> None:
        # plan_id -> Plan. TTL-evicting; values touched on every mutation
        # so an in-flight plan never expires while it's still being worked.
        self._plans: _TTLStore = _TTLStore(ttl_seconds=ttl_seconds)
        # plan_id -> step_index -> monotonic start time. Used to fill
        # duration_ms on complete_step / fail_step. Kept separate from the
        # frozen Plan so the lifecycle stays immutable.
        self._step_starts: _TTLStore = _TTLStore(ttl_seconds=ttl_seconds)
        # `with self._lock:` is a NO-OP context (nullcontext) — the tracker
        # is single-event-loop by design (see module docstring). The blocks
        # are kept as structure markers so a future variant that needs real
        # locking can swap in an ``asyncio.Lock`` without touching every
        # call site. DO NOT replace with ``threading.RLock`` — that would
        # be false advertising under asyncio.
        self._lock = nullcontext()

    # --- queries ----------------------------------------------------------

    def get(self, plan_id: str, *, session_id: str | None = None) -> Plan:
        """Return the plan, or raise :class:`PlanNotFound`.

        If ``session_id`` is provided, also verify it matches the plan's
        owning session — cross-session access raises :class:`SessionMismatch`
        (which inherits from :class:`PermissionError` so MCP boundary code
        can map it to a structured 'forbidden' response)."""
        try:
            plan = self._plans[plan_id]
        except KeyError as e:
            raise PlanNotFound(plan_id) from e
        if session_id is not None and plan.session_id != session_id:
            raise SessionMismatch(
                f"plan {plan_id!r} belongs to session {plan.session_id!r}, not {session_id!r}"
            )
        return plan

    def list_for_session(self, session_id: str) -> list[Plan]:
        """Every plan recorded for one session, in declaration order."""
        return [p for p in self._plans.values() if p.session_id == session_id]

    # --- mutations: lifecycle --------------------------------------------

    def declare_plan(
        self,
        session_id: str,
        steps: list[str | dict[str, Any]],
    ) -> Plan:
        """Register a new plan, return the live Plan.

        ``steps`` accepts a mix of:
          - plain strings (label only) — ``"Search SERP"``
          - dicts with optional keys: ``label``, ``active_form``,
            ``depends_on`` (list of int), ``metadata`` (dict)

        Empty ``steps`` is rejected with :class:`ValueError` — a checklist
        with zero rows is a UI bug, never a useful state. The MCP server
        catches this at the boundary."""
        if not steps:
            raise ValueError("steps must not be empty")

        with self._lock:
            plan_id = uuid.uuid4().hex[:16]  # 64 bits — collision-safe for the realistic in-memory volume
            step_objs: list[Step] = []
            for i, raw in enumerate(steps):
                if isinstance(raw, str):
                    step_objs.append(Step(index=i, label=raw))
                    continue
                if not isinstance(raw, dict):
                    raise ValueError(f"step at index {i} must be str or dict, got {type(raw).__name__}")
                label = raw.get("label")
                if not isinstance(label, str) or not label:
                    raise ValueError(f"step at index {i} missing required 'label' string")
                depends_on = tuple(raw.get("depends_on") or ())
                for dep in depends_on:
                    if not isinstance(dep, int) or dep < 0 or dep >= i:
                        # A step can only depend on EARLIER steps — forbids
                        # cycles structurally without a DAG validator.
                        raise ValueError(
                            f"step {i} dependency {dep!r} is invalid; must reference an earlier step"
                        )
                step_objs.append(Step(
                    index=i,
                    label=label,
                    active_form=raw.get("active_form", "") or "",
                    depends_on=depends_on,
                    metadata=raw.get("metadata") or None,
                ))
            plan = Plan(
                plan_id=plan_id,
                session_id=session_id,
                status=PlanStatus.DECLARED,
                steps=tuple(step_objs),
            )
            self._plans[plan_id] = plan
            self._step_starts[plan_id] = {}
            return plan

    def start_step(
        self,
        plan_id: str,
        step_index: int,
        *,
        session_id: str | None = None,
    ) -> Step:
        """Mark a step RUNNING. The plan flips to RUNNING on the first call.

        Idempotent: calling ``start_step`` twice on the same RUNNING step is
        a no-op (returns the existing Step without resetting ``t0``). Raises
        :class:`StepAlreadyTerminal` if the step has already settled, and
        :class:`DependencyUnmet` if any ``depends_on`` step isn't DONE yet."""
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            self._check_index(plan, step_index)
            current = plan.steps[step_index]
            if current.status in TERMINAL_STEP_STATES:
                raise StepAlreadyTerminal(
                    f"step {step_index} of plan {plan_id} is already {current.status.value}"
                )
            if current.status is StepStatus.RUNNING:
                # G11: idempotent — don't reset t0, don't re-emit.
                return current
            # G6: dependencies must all be DONE before this step can start.
            for dep_idx in current.depends_on:
                dep = plan.steps[dep_idx]
                if dep.status is not StepStatus.DONE:
                    raise DependencyUnmet(
                        f"step {step_index} depends on step {dep_idx} which is {dep.status.value}, not done"
                    )
            self._step_starts[plan_id][step_index] = time.monotonic()
            step = replace(current, status=StepStatus.RUNNING)
            return self._replace_step(plan, step_index, step, plan_status=PlanStatus.RUNNING)

    def complete_step(
        self,
        plan_id: str,
        step_index: int,
        summary: str = "",
        *,
        session_id: str | None = None,
    ) -> Step:
        """Mark a step DONE with measured ``duration_ms``. Plan flips to
        COMPLETED only when every step is in a terminal state (DONE/SKIPPED)."""
        return self._end_step(
            plan_id, step_index, StepStatus.DONE,
            session_id=session_id, summary=summary,
        )

    def fail_step(
        self,
        plan_id: str,
        step_index: int,
        error: str = "",
        *,
        session_id: str | None = None,
    ) -> Step:
        """Mark a step FAILED. The plan goes to FAILED overall when all
        steps are settled — partial-success isn't a plan outcome."""
        return self._end_step(
            plan_id, step_index, StepStatus.FAILED,
            session_id=session_id, error=error,
        )

    def cancel_step(
        self,
        plan_id: str,
        step_index: int,
        reason: str = "",
        *,
        session_id: str | None = None,
    ) -> Step:
        """Mark a step CANCELLED — for client-initiated cancellation while
        the step was RUNNING (MCP ``notifications/cancelled`` semantics). The
        plan goes to CANCELLED if no step succeeded, otherwise COMPLETED on
        the next settle."""
        return self._end_step(
            plan_id, step_index, StepStatus.CANCELLED,
            session_id=session_id, error=reason,
        )

    def note_step(
        self,
        plan_id: str,
        step_index: int,
        note: str,
        *,
        session_id: str | None = None,
    ) -> Step:
        """Append a progress note to a RUNNING step — never overwrites.

        Useful when a step takes many seconds and the agent wants to surface
        intermediate context ("scraped page 1 of 4 ...") without leaving the
        ``summary`` empty. Rejected on terminal steps (append-only)."""
        if not note:
            return self.get(plan_id, session_id=session_id).steps[step_index]
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            self._check_index(plan, step_index)
            current = plan.steps[step_index]
            if current.status in TERMINAL_STEP_STATES:
                raise StepAlreadyTerminal(
                    f"cannot note step {step_index} of plan {plan_id}: already {current.status.value}"
                )
            new_notes = current.notes + (note,)
            step = replace(current, notes=new_notes)
            new_steps = tuple(step if i == step_index else s for i, s in enumerate(plan.steps))
            self._plans[plan_id] = replace(plan, steps=new_steps)
            return step

    # --- mutations: replanning -------------------------------------------

    def insert_step(
        self,
        plan_id: str,
        after_index: int,
        spec: str | dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> Plan:
        """Insert a new step right after ``after_index``. Re-numbers later
        steps' ``index`` and any ``depends_on`` references that point past
        the insertion point. Plan must not be terminal; the new step is
        always inserted in PENDING.

        Use ``after_index=-1`` to prepend at the head of the plan."""
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            if plan.status in TERMINAL_PLAN_STATES:
                raise PlanAlreadyTerminal(
                    f"plan {plan_id} is {plan.status.value}; cannot insert step"
                )
            if after_index < -1 or after_index >= plan.step_count:
                raise StepIndexInvalid(
                    f"after_index {after_index} out of range for plan {plan_id} ({plan.step_count} steps)"
                )
            new_index = after_index + 1
            new_step = self._build_step(new_index, spec)
            # Renumber later steps and bump any depends_on references that
            # crossed the insertion point.
            shifted: list[Step] = []
            for s in plan.steps:
                if s.index < new_index:
                    shifted.append(s)
                    continue
                bumped_deps = tuple(d + 1 if d >= new_index else d for d in s.depends_on)
                shifted.append(replace(s, index=s.index + 1, depends_on=bumped_deps))
            new_steps = tuple(sorted([*shifted, new_step], key=lambda s: s.index))
            new_plan = replace(plan, steps=new_steps)
            self._plans[plan_id] = new_plan
            return new_plan

    def replan(
        self,
        plan_id: str,
        from_index: int,
        new_steps: list[str | dict[str, Any]],
        *,
        session_id: str | None = None,
    ) -> Plan:
        """Replace every step from ``from_index`` onwards with ``new_steps``.

        Steps before ``from_index`` keep their state (must all be in a
        terminal state — you can't replan around a RUNNING step without
        cancelling it first). New steps are inserted as PENDING with
        renumbered indexes and validated ``depends_on`` (must reference
        steps that exist post-replan)."""
        if not new_steps:
            raise ValueError("new_steps must not be empty for replan")
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            if plan.status in TERMINAL_PLAN_STATES:
                raise PlanAlreadyTerminal(
                    f"plan {plan_id} is {plan.status.value}; cannot replan"
                )
            if from_index < 0 or from_index > plan.step_count:
                raise StepIndexInvalid(
                    f"from_index {from_index} out of range for plan {plan_id} ({plan.step_count} steps)"
                )
            kept = list(plan.steps[:from_index])
            for s in kept:
                if s.status not in TERMINAL_STEP_STATES:
                    raise StepAlreadyTerminal(
                        f"cannot replan past step {s.index} which is {s.status.value} (must be terminal)"
                    )
            # The wipe also drops any step_starts that referenced removed steps.
            kept_indexes = {s.index for s in kept}
            self._step_starts[plan_id] = {
                k: v for k, v in self._step_starts.get(plan_id, {}).items() if k in kept_indexes
            }
            replacements: list[Step] = []
            for offset, raw in enumerate(new_steps):
                step = self._build_step(from_index + offset, raw)
                # Replan deps must reference EARLIER steps (existing kept ones
                # or earlier new ones) — same rule as declare_plan: no cycles.
                for dep in step.depends_on:
                    if dep < 0 or dep >= step.index:
                        raise ValueError(
                            f"replan step {step.index} depends on {dep!r}; must reference an earlier step"
                        )
                replacements.append(step)
            new_plan_steps = tuple([*kept, *replacements])
            new_plan = replace(plan, steps=new_plan_steps)
            self._plans[plan_id] = new_plan
            return new_plan

    def cancel_plan(
        self,
        plan_id: str,
        reason: str = "",
        *,
        session_id: str | None = None,
    ) -> Plan:
        """Cancel the entire plan: any non-terminal step is marked CANCELLED,
        the plan goes to CANCELLED. Idempotent on an already-CANCELLED plan;
        rejects on COMPLETED/FAILED (those are terminal, not cancellable)."""
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            if plan.status is PlanStatus.CANCELLED:
                return plan
            if plan.status in (PlanStatus.COMPLETED, PlanStatus.FAILED):
                raise PlanAlreadyTerminal(
                    f"plan {plan_id} is {plan.status.value}; cannot cancel a settled plan"
                )
            new_steps = tuple(
                replace(s, status=StepStatus.CANCELLED, error=reason or s.error)
                if s.status not in TERMINAL_STEP_STATES
                else s
                for s in plan.steps
            )
            new_plan = replace(plan, steps=new_steps, status=PlanStatus.CANCELLED)
            self._plans[plan_id] = new_plan
            return new_plan

    def finalize_plan(
        self,
        plan_id: str,
        *,
        session_id: str | None = None,
    ) -> Plan:
        """Settle the plan: any PENDING/RUNNING step is marked SKIPPED, the
        plan flips to COMPLETED (no failures), FAILED (any step failed), or
        CANCELLED (any cancelled step, no DONE). Idempotent."""
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            if plan.status in TERMINAL_PLAN_STATES:
                return plan
            new_steps = tuple(
                replace(s, status=StepStatus.SKIPPED)
                if s.status in (StepStatus.PENDING, StepStatus.RUNNING)
                else s
                for s in plan.steps
            )
            any_failed = any(s.status is StepStatus.FAILED for s in new_steps)
            any_cancelled = any(s.status is StepStatus.CANCELLED for s in new_steps)
            any_done = any(s.status is StepStatus.DONE for s in new_steps)
            if any_failed:
                final_status = PlanStatus.FAILED
            elif any_cancelled and not any_done:
                final_status = PlanStatus.CANCELLED
            else:
                final_status = PlanStatus.COMPLETED
            new_plan = replace(plan, steps=new_steps, status=final_status)
            self._plans[plan_id] = new_plan
            return new_plan

    # --- helpers ----------------------------------------------------------

    def _build_step(self, index: int, spec: Any) -> Step:
        # Accepts `Any` rather than the narrow `str | dict` because specs cross
        # the MCP boundary as arbitrary JSON; we validate shape at the boundary
        # instead of trusting the type hint of an upstream caller.
        if isinstance(spec, str):
            return Step(index=index, label=spec)
        if not isinstance(spec, dict):
            raise ValueError(f"step spec must be str or dict, got {type(spec).__name__}")
        label = spec.get("label")
        if not isinstance(label, str) or not label:
            raise ValueError(f"step spec at index {index} missing required 'label' string")
        return Step(
            index=index,
            label=label,
            active_form=spec.get("active_form", "") or "",
            depends_on=tuple(spec.get("depends_on") or ()),
            metadata=spec.get("metadata") or None,
        )

    def _check_index(self, plan: Plan, step_index: int) -> None:
        if not (0 <= step_index < plan.step_count):
            raise StepIndexInvalid(
                f"step_index {step_index} out of range for plan {plan.plan_id} ({plan.step_count} steps)"
            )

    def _end_step(
        self,
        plan_id: str,
        step_index: int,
        status: StepStatus,
        *,
        session_id: str | None = None,
        summary: str = "",
        error: str = "",
    ) -> Step:
        with self._lock:
            plan = self.get(plan_id, session_id=session_id)
            self._check_index(plan, step_index)
            current = plan.steps[step_index]
            if current.status in TERMINAL_STEP_STATES:
                # G10: terminal states are immutable; late retries of
                # complete/fail/cancel don't regress or overwrite state.
                raise StepAlreadyTerminal(
                    f"step {step_index} of plan {plan_id} is already {current.status.value}"
                )
            t0 = self._step_starts.get(plan_id, {}).get(step_index)
            # If the agent skipped start_step (some models do), we have no t0 —
            # leave duration_ms None rather than fabricating one.
            dur = int((time.monotonic() - t0) * 1000) if t0 is not None else None
            step = replace(current, status=status, duration_ms=dur, summary=summary, error=error)
            # Decide the plan's overall status from the new step set.
            new_steps = list(plan.steps)
            new_steps[step_index] = step
            any_failed = any(s.status is StepStatus.FAILED for s in new_steps)
            any_cancelled = any(s.status is StepStatus.CANCELLED for s in new_steps)
            any_done = any(s.status is StepStatus.DONE for s in new_steps)
            all_settled = all(s.status in TERMINAL_STEP_STATES for s in new_steps)
            if all_settled:
                if any_failed:
                    new_plan_status = PlanStatus.FAILED
                elif any_cancelled and not any_done:
                    new_plan_status = PlanStatus.CANCELLED
                else:
                    new_plan_status = PlanStatus.COMPLETED
            else:
                new_plan_status = PlanStatus.RUNNING
            return self._replace_step(plan, step_index, step, plan_status=new_plan_status)

    def _replace_step(self, plan: Plan, step_index: int, step: Step, *, plan_status: PlanStatus) -> Step:
        new_steps = tuple(step if i == step_index else s for i, s in enumerate(plan.steps))
        self._plans[plan.plan_id] = replace(plan, steps=new_steps, status=plan_status)
        return step
