"""Persona / character-integrity primitives for LLM-driven applications.

Three detector classes for the three failure modes of character-driven
LLM responses:

    - `BreakDetector`             — hard identity leaks (retry-worthy)
    - `AntiPatternMonitor`        — soft drift toward assistant tone (log)
    - `ClarificationDumpDetector` — punting the task back at the user

Plus `sanitize()` for last-resort cleanup when retries fail, and a `packs`
namespace of built-in pattern packs (English + Spanish).

All matching is deterministic regex — zero LLM calls at detection time,
zero embeddings, zero training data needed.

Origin: extracted from the production Discord persona bot
(`insult/core/character/detection.py`) and generalized for reuse across
deployments.
"""

from typing import Any

from fi_core.persona import packs
from fi_core.persona.detect import (
    AntiPatternMonitor,
    BreakDetector,
    ClarificationDumpDetector,
    sanitize,
)
from fi_core.persona.loader import PersonaLoader
from fi_core.persona.types import DetectionResult

__all__ = [
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "AntiPatternMonitor",
    "BreakDetector",
    "ClarificationDumpDetector",
    "DetectionResult",
    "PersonaLoader",
    "packs",
    "sanitize",
]


# The MCP server pulls the optional `mcp` extra. Lazy-load its symbols via PEP 562
# so importing `fi_core.persona` (for the detectors or PersonaLoader) does NOT
# require the extra — only touching MCP_SERVER_NAME / MCP_TOOLS does.
def __getattr__(name: str) -> Any:
    if name in ("MCP_SERVER_NAME", "MCP_TOOLS"):
        from fi_core.persona import mcp_server

        return getattr(mcp_server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
