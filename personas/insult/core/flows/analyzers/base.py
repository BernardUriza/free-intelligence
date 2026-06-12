"""Protocol and shared context for flow analyzers.

An Analyzer is anything that takes a `FlowContext` and produces a
structured result dataclass. The `FlowPipeline` coordinator runs the
registered analyzers in order; new flows can be added by implementing
this protocol and appending the analyzer to the pipeline's list.

Why a Protocol and not an ABC: Protocols give us structural typing, so
any object with the right shape qualifies as an Analyzer. That means
tests can pass in a small dataclass / callable wrapper without
inheriting — nice for exercising cross-flow overrides in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from personas.insult.core.flows.history import ExpressionHistory
    from personas.insult.core.presets import PresetSelection


@dataclass
class FlowContext:
    """Everything the analyzers need to examine a single turn.

    Built once by `FlowPipeline.run()` and passed to every analyzer so
    each one can pluck the fields it cares about without re-deriving
    common values (like the list of user messages from recent_messages).

    `expression_history` + `context_key` are optional because some
    callers (tests, validators) invoke analyzers without the full
    anti-repetition machinery — in that case ExpressionAnalyzer falls
    back to empty recent-shapes/flavors lists.
    """

    current_message: str
    recent_messages: list[dict]
    preset: PresetSelection
    # Derived: last N user messages, extracted once.
    user_messages: list[str] = field(default_factory=list)
    expression_history: ExpressionHistory | None = None
    context_key: str | None = None


class Analyzer(Protocol):
    """Protocol that every flow analyzer must satisfy.

    Each concrete analyzer owns ONE flow's logic end-to-end:
    - Produces a typed analysis result.
    - Emits a structured log event describing what it decided and why.
    """

    name: str
    """Short identifier, used in logs (e.g. 'epistemic', 'pressure')."""

    def analyze(self, ctx: FlowContext, prior: dict[str, Any]) -> Any:
        """Compute the flow result.

        `prior` is a dict of results already produced by earlier analyzers
        in the pipeline (keyed by analyzer name). This is how dependencies
        flow: for example the Expression analyzer reads prior['epistemic']
        and prior['pressure'] to decide shape/flavor. If your analyzer is
        independent, ignore `prior`.
        """
        ...

    def log_event(self, result: Any) -> None:
        """Emit the structured telemetry event for this flow's result."""
        ...
