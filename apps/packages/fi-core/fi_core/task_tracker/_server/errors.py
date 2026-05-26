"""Exception → MCP error code mapping for the task_tracker server.

The MCP server boundary turns tracker exceptions into structured error
payloads (``{"error": str, "code": str}``). v1 of the server had a
hand-rolled try/except in every one of the 11 tool handlers, mapping the
same exception types to the same codes — ~150 lines of duplication that
all changes in lockstep when a new error class is added.

This module centralizes the mapping in :data:`EXCEPTION_CODES` and exposes
:func:`tracker_exceptions_to_error` as an awaitable context manager. Every
handler wraps its body with this and the boundary stays uniform: add a new
tracker exception → add one entry here, every handler picks it up.

If a future tracker call raises an exception NOT in the map, it propagates
— the MCP server returns a 500-ish to the agent, which is the right default
for an unknown failure mode (better than a silent ``{"error": "..."}`` that
hides a programming bug)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from ..tracker import (
    DependencyUnmet,
    PlanAlreadyTerminal,
    PlanNotFound,
    SessionMismatch,
    StepAlreadyTerminal,
    StepIndexInvalid,
)
from .serializers import error_payload


#: Tracker exception type → MCP error code. Ordering matters only for human
#: maintenance — the lookup is a dict, not a list of try-blocks.
EXCEPTION_CODES: dict[type[Exception], str] = {
    PlanNotFound: "plan_not_found",
    SessionMismatch: "session_mismatch",
    StepIndexInvalid: "step_index_invalid",
    StepAlreadyTerminal: "step_terminal",
    PlanAlreadyTerminal: "plan_terminal",
    DependencyUnmet: "dependency_unmet",
    # ValueError isn't a tracker class — it's stdlib — but the tracker raises
    # it for boundary validation (empty steps, malformed dict). Mapped to a
    # generic "invalid_input" so the handler decides when to override.
    ValueError: "invalid_input",
}


class _TrackerCallResult:
    """Sentinel returned by :func:`tracker_call` — carries either the result
    or the error payload, so the caller can short-circuit cleanly."""

    __slots__ = ("error", "_has_error")

    def __init__(self) -> None:
        self.error: dict[str, Any] | None = None
        self._has_error: bool = False

    @property
    def failed(self) -> bool:
        return self._has_error

    def set_error(self, payload: dict[str, Any]) -> None:
        self.error = payload
        self._has_error = True


@contextmanager
def tracker_call(
    *, value_error_code: str | None = None,
) -> Iterator[_TrackerCallResult]:
    """Wrap a tracker call site, converting known exceptions to error payloads.

    Usage::

        with tracker_call() as r:
            step = get_tracker().start_step(plan_id, step_index)
        if r.failed:
            return r.error
        return step_dict(plan_id, step)

    ``value_error_code`` lets a handler override the ValueError default code
    (e.g. ``"invalid_steps"`` for ``declare_plan``, ``"invalid_new_steps"``
    for ``replan``) without losing the rest of the mapping."""
    result = _TrackerCallResult()
    try:
        yield result
    except tuple(EXCEPTION_CODES) as exc:
        code = EXCEPTION_CODES[type(exc)]
        if isinstance(exc, ValueError) and value_error_code is not None:
            code = value_error_code
        result.set_error(error_payload(str(exc), code=code))
