"""3-tier model router — maps preset + flow + disclosure severity to a model choice.

Pure, zero-I/O. Deterministic given its inputs. Caller wires real model ids
via the three *_model parameters so tests can pass dummy strings.

Tiers:
- CASUAL (Haiku): DEFAULT_ABRASIVE, PLAYFUL_ROAST, META_DEFLECTION.
- DEPTH (Sonnet): INTELLECTUAL_PRESSURE, ARC, RELATIONAL_PROBE. Also the
  universal fallback when casual output fails a guard.
- CRISIS (Opus): RESPECTFUL_SERIOUS, severe disclosure, or vulnerable+hard
  pressure. Budget-capped per user on a 24h sliding window.

Fallback shape is always (primary, depth). Opus and Sonnet fall back to
Sonnet — no point reruning against an identical model; the reinforced-prompt
retry inside the runner already handles that edge.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from insult.core.flows import FlowAnalysis, UserState
from insult.core.presets import PresetMode, PresetSelection


class ModelTier(StrEnum):
    CASUAL = "casual"
    DEPTH = "depth"
    CRISIS = "crisis"


_CASUAL_PRESETS = {
    PresetMode.DEFAULT_ABRASIVE,
    PresetMode.PLAYFUL_ROAST,
    PresetMode.META_DEFLECTION,
}
_DEPTH_PRESETS = {
    PresetMode.INTELLECTUAL_PRESSURE,
    PresetMode.ARC,
    PresetMode.RELATIONAL_PROBE,
}


@dataclass(frozen=True)
class ModelChoice:
    primary: str
    fallback: str
    tier: ModelTier
    reason: str


def select_model(
    preset: PresetSelection,
    flow: FlowAnalysis,
    disclosure_severity: int,
    casual_model: str,
    depth_model: str,
    crisis_model: str,
    *,
    opus_24h_count: int = 0,
    opus_24h_cap: int = 20,
) -> ModelChoice:
    """Pick (primary, fallback) for a turn. Never touches the network."""
    is_crisis = (
        preset.mode == PresetMode.RESPECTFUL_SERIOUS
        or disclosure_severity >= 3
        or (flow.pressure.detected_state == UserState.VULNERABLE and flow.pressure.pressure_level >= 4)
    )
    if is_crisis and opus_24h_count < opus_24h_cap:
        return ModelChoice(crisis_model, depth_model, ModelTier.CRISIS, "crisis_trigger")
    if is_crisis:
        return ModelChoice(depth_model, depth_model, ModelTier.DEPTH, "opus_cap_reached")
    if preset.mode in _DEPTH_PRESETS:
        return ModelChoice(depth_model, depth_model, ModelTier.DEPTH, "depth_preset")
    if preset.mode in _CASUAL_PRESETS:
        return ModelChoice(casual_model, depth_model, ModelTier.CASUAL, "casual_preset")
    # Unknown / future preset: default to Sonnet. Better waste money than
    # ship garbage through Haiku on an unclassified path.
    return ModelChoice(depth_model, depth_model, ModelTier.DEPTH, "unknown_preset_default_to_depth")


class OpusBudget:
    """Per-user rolling 24h counter of Opus calls.

    In-memory only. Resets on container restart — acceptable because a
    restart during a crisis conversation would already disrupt continuity,
    and persisting across restarts would make the cap feel unpredictable
    after infra events.
    """

    def __init__(self, cap: int = 20, window_seconds: int = 24 * 3600):
        self._cap = cap
        self._window = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    @property
    def cap(self) -> int:
        return self._cap

    def count(self, user_id: str, now: float | None = None) -> int:
        """Return the number of Opus calls by this user in the last 24h."""
        now = now if now is not None else time.time()
        cutoff = now - self._window
        with self._lock:
            q = self._events.get(user_id)
            if not q:
                return 0
            while q and q[0] < cutoff:
                q.popleft()
            return len(q)

    def record(self, user_id: str, now: float | None = None) -> int:
        """Record a new Opus call. Returns the updated count."""
        now = now if now is not None else time.time()
        cutoff = now - self._window
        with self._lock:
            q = self._events.setdefault(user_id, deque())
            while q and q[0] < cutoff:
                q.popleft()
            q.append(now)
            return len(q)
