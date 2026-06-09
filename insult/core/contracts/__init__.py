"""Neutral shared contracts — enums + dataclasses with NO behavior coupling.

These are the vocabulary types (preset modes, flow analysis results) that both
the lightweight HOST (routing/delivery) and the SMART persona internals
(flows/presets analyzers) need to agree on. Extracting them here lets host-facing
code depend on neutral contracts instead of reaching into smart/persona packages
(see `tests/test_arch_import_boundaries.py` and
`.claude/plans/khimeras_demux_destilado.md`).

Leaf package: depends only on the stdlib. Both `insult.core.flows.types` and
`insult.core.presets.types` now re-export from here for backwards compatibility,
so `insult.core.flows`/`insult.core.presets` keep their public surface unchanged
and enum identity is preserved (each type is defined exactly once, here).
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
from insult.core.contracts.history import (
    EXPRESSION_HISTORY_MAXLEN,
    ExpressionHistory,
)
from insult.core.contracts.memory import DebugMemoryPort
from insult.core.contracts.presets import (
    PresetMode,
    PresetModifier,
    PresetSelection,
)

__all__ = [
    "EXPRESSION_HISTORY_MAXLEN",
    "AwarenessAnalysis",
    "ConversationPattern",
    "DebugMemoryPort",
    "EpistemicAnalysis",
    "EpistemicMove",
    "ExpressionAnalysis",
    "ExpressionHistory",
    "FlowAnalysis",
    "PresetMode",
    "PresetModifier",
    "PresetSelection",
    "PressureAnalysis",
    "ResponseShape",
    "StyleFlavor",
    "UserState",
]
