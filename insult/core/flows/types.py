"""Backwards-compatible shim for the flow vocabulary.

The enums and dataclasses moved to `insult.core.contracts.flows` (a neutral,
stdlib-only contracts module) so host-facing code can depend on them without
crossing the host→smart import boundary. This module re-exports them so existing
callers (`from insult.core.flows.types import FlowAnalysis`, the package barrel,
the analyzers, the validator) keep working unchanged.

Enum identity is preserved: every type is defined exactly once in
`insult.core.contracts.flows` and imported here — there is no redefinition.
"""

from __future__ import annotations

from insult.core.contracts.flows import (
    AwarenessAnalysis,
    ConversationPattern,
    EpistemicAnalysis,
    EpistemicMove,
    ExpressionAnalysis,
    FlowAnalysis,
    PressureAnalysis,
    ResponseShape,
    StyleFlavor,
    UserState,
)

__all__ = [
    "AwarenessAnalysis",
    "ConversationPattern",
    "EpistemicAnalysis",
    "EpistemicMove",
    "ExpressionAnalysis",
    "FlowAnalysis",
    "PressureAnalysis",
    "ResponseShape",
    "StyleFlavor",
    "UserState",
]
