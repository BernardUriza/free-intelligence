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

from fi_core.persona import packs
from fi_core.persona.detect import (
    AntiPatternMonitor,
    BreakDetector,
    ClarificationDumpDetector,
    sanitize,
)
from fi_core.persona.mcp_server import (
    MCP_SERVER_NAME,
    MCP_TOOLS,
)
from fi_core.persona.types import DetectionResult

__all__ = [
    "AntiPatternMonitor",
    "BreakDetector",
    "ClarificationDumpDetector",
    "DetectionResult",
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "packs",
    "sanitize",
]
