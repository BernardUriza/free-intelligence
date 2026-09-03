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


@dataclass(frozen=True, repr=False)
class RemoteTool:
    """An HTTP MCP server the CALLER hosts and the door only wires (#48).

    This is not the RCE the registry doctrine bans: no command ever crosses the
    wire — the agent makes an outbound HTTPS call to a host the OPERATOR chose.
    The wire names the url; the environment defines the trust: its origin must
    be listed in ``AIRE_REMOTE_TOOL_ORIGINS`` or the door refuses the turn.

    ``headers`` carry the caller's credential to its OWN server (a bearer the
    runner mints for itself). They are a secret in transit: the redacting
    ``__repr__`` below is load-bearing — TurnSpec is printed on every REBIND."""

    name: str
    url: str
    headers: tuple[tuple[str, str], ...] = ()

    def __repr__(self) -> str:
        return f"RemoteTool(name={self.name!r}, url={self.url!r}, headers=<{len(self.headers)} redacted>)"


@dataclass(frozen=True)
class TurnSpec:
    """One turn's requested shape, threaded whole through the turn path (#29).
    Everything here binds when the session's pooled client is (re)born — the SDK
    takes it at construction — and a turn that asks for a DIFFERENT shape drops
    the warm client first (#38), so remote_tools rebind like model and tools."""

    mode: str
    tools: tuple[str, ...] = ()
    model: str | None = None
    remote_tools: tuple[RemoteTool, ...] = ()


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
    subtype: str | None = None
    """The SDK result's own verdict (`success`, `error_max_budget_usd`, …) — on
    the wire so a consumer can tell a cut turn from a clean one without guessing
    from its token counts."""


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
