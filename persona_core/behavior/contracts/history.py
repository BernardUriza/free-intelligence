"""Anti-repetition tracking for shape+flavor selection.

Neutral contract: a stdlib-only rolling-buffer the host constructs and hands to
the flow pipeline (shared state between host and smart, no smart deps). Moved
here from `insult.core.flows.history` during the contracts batch so host-facing
code (the chat cog) can construct it without crossing the host→smart import
boundary. `insult.core.flows.history` now re-exports from here (identity
preserved).

Lives separate from the ExpressionAnalyzer so it can be:
- persisted independently (SQLite round-trip via to_records / load_from_records),
- shared across analyzer instances if we ever parallelize,
- tested in isolation.
"""

from __future__ import annotations

from collections import deque

from persona_core.behavior.contracts.flows import ResponseShape, StyleFlavor

EXPRESSION_HISTORY_MAXLEN = 10


class ExpressionHistory:
    """Per-context rolling buffer of (shape, flavor) selections.

    `context_key` is typically `"{channel_id}:{user_id}"` so different
    users in the same channel have independent repetition avoidance.
    The buffer caps at `maxlen` entries to prevent unbounded growth while
    still giving the analyzer enough history to dodge recent choices."""

    def __init__(self, maxlen: int = EXPRESSION_HISTORY_MAXLEN):
        self._history: dict[str, deque] = {}
        self._maxlen = maxlen

    def get(self, key: str) -> deque:
        if key not in self._history:
            self._history[key] = deque(maxlen=self._maxlen)
        return self._history[key]

    def record(self, key: str, shape: ResponseShape, flavor: StyleFlavor) -> None:
        self.get(key).append((shape.value, flavor.value))

    def recent_shapes(self, key: str, n: int = 3) -> list[str]:
        return [s for s, _ in list(self.get(key))[-n:]]

    def recent_flavors(self, key: str, n: int = 3) -> list[str]:
        return [f for _, f in list(self.get(key))[-n:]]

    def load_from_records(self, key: str, records: list[tuple[str, str]]) -> None:
        """Restore history from persisted (shape, flavor) pairs."""
        q: deque = deque(maxlen=self._maxlen)
        for shape, flavor in records[-self._maxlen :]:
            q.append((shape, flavor))
        self._history[key] = q

    def to_records(self, key: str) -> list[tuple[str, str]]:
        """Export history as list of (shape, flavor) for persistence."""
        return list(self.get(key))
