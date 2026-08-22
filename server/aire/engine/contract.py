"""The engine's typed results — copied from fi-runner's contract, minimal:
only what the interface needs to show."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

CostSink = Callable[[float], Awaitable[None]]
"""What a turn's dollars are reported to. The engine never learns WHOSE ceiling
it is feeding — it hands over a number, and the HTTP surface knows the key."""


class BudgetExceeded(Exception):
    """Raised when the cumulative spend ceiling is hit — the server maps it to a
    402 so the caller learns why, instead of a silent stall."""


class SlotBusy(Exception):
    """Raised when a turn waited for a RAM slot longer than AIRE_SLOT_WAIT_S:
    every client slot is a live turn. The server maps it to 503 (retry) — the
    caller was queued (backpressure), not dropped, and the box did not OOM."""


@dataclass(frozen=True)
class TurnSpec:
    """One turn's requested shape, threaded whole through the turn path (#29).
    All three bind when the session's pooled client is (re)born — the SDK takes
    them at construction — so a live session keeps the shape it started with."""

    mode: str
    tools: tuple[str, ...] = ()
    model: str | None = None


@dataclass(frozen=True)
class ToolCall:
    name: str
    input: dict[str, Any] | None = None
    id: str | None = None
    is_error: bool | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class TurnResult:
    text: str
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    model: str | None = None
    """The model that actually answered — read off the assistant messages, never
    echoed from the request (#29 gap 3: provenance, not an unhonoured promise)."""


@dataclass(frozen=True)
class GuardOutcome:
    """What one guard found in a turn (`guards/registry.py`).

    `metadata` carries observational findings (severity, matched patterns).
    `text_override` replaces the response text. `retry` advises the caller to
    re-run the turn with `reinforcement` appended to the system prompt — the
    engine never auto-retries: a guard detects and advises, the turn loop owns
    the policy."""

    metadata: dict[str, Any] = field(default_factory=dict)
    text_override: str | None = None
    retry: bool = False
    reinforcement: str = ""

    @property
    def clean(self) -> bool:
        """True when the guard found nothing actionable (no edit, no retry)."""
        return self.text_override is None and not self.retry


@runtime_checkable
class Guard(Protocol):
    """A deterministic safety net the engine runs in-process every turn."""

    name: str

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        """Inspect a turn's `response_text` (plus optional `context` strings, e.g.
        the user's own message) and return a `GuardOutcome`. `final` is True on
        the last allowed attempt: a transformational guard stops asking for a
        retry and cleans up instead, so the turn ships a best-effort result."""
        ...
