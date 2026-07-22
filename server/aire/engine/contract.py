"""The engine's typed results — copied from fi-runner's contract, minimal:
only what the interface needs to show."""

from dataclasses import dataclass
from typing import Any


class BudgetExceeded(Exception):
    """Raised when the cumulative spend ceiling is hit — the server maps it to a
    402 so the caller learns why, instead of a silent stall."""


class SlotBusy(Exception):
    """Raised when a turn waited for a RAM slot longer than AIRE_SLOT_WAIT_S:
    every client slot is a live turn. The server maps it to 503 (retry) — the
    caller was queued (backpressure), not dropped, and the box did not OOM."""


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
