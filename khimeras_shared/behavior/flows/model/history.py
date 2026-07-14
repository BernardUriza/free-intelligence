"""Backwards-compatible shim for the expression-history buffer.

`ExpressionHistory` and `EXPRESSION_HISTORY_MAXLEN` moved to
`insult.core.contracts.history` (a neutral, stdlib-only contracts module) so the
host can construct the buffer without crossing the host→smart import boundary.
This module re-exports them so existing callers (the `flows` package barrel, the
ExpressionAnalyzer, the chat pipeline) keep working unchanged — class identity
is preserved (defined exactly once, in contracts).
"""

from __future__ import annotations

from khimeras_shared.behavior.contracts.history import EXPRESSION_HISTORY_MAXLEN, ExpressionHistory

__all__ = [
    "EXPRESSION_HISTORY_MAXLEN",
    "ExpressionHistory",
]
