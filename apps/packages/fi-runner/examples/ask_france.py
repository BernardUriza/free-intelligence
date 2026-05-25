#!/usr/bin/env python3
"""Live ClaudeCodeBackend query — ask about French history, show the telemetry.

A real turn through the Claude Agent SDK (Max subscription via OAuth). The SDK
reads auth from the ENVIRONMENT, so this file holds NO secret. Run with the
token only in the process env:

    CLAUDE_CODE_OAUTH_TOKEN=... python3 examples/ask_france.py

Bloquea las tools de archivos/shell (turno de solo texto) y muestra los eventos
de telemetría (turn_completed) emitidos por el Runner en un run real.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

from fi_runner import ClaudeCodeBackend, PermissionMode, Runner, ToolPolicy  # noqa: E402


def event_sink(event: str, fields: dict) -> None:
    print(f"  [event] {event:16s} {fields}")


async def main() -> None:
    if not (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")):
        print("  ! No auth in env. Set CLAUDE_CODE_OAUTH_TOKEN (or ANTHROPIC_API_KEY).")
        return
    logging.basicConfig(level=logging.INFO, format="  [log] %(name)s | %(message)s")

    runner = Runner(
        backend=ClaudeCodeBackend(default_model="sonnet"),
        persona="Eres un historiador conciso. Responde en español, claro y directo, sin relleno.",
        tool_policy=ToolPolicy(
            builtin_disallowed=["Bash", "Write", "Edit", "Read"],  # text-only turn
            permission_mode=PermissionMode.DEFAULT,
        ),
        on_event=event_sink,
    )

    question = (
        "¿Cuáles fueron las tres causas principales de la Revolución Francesa de 1789? "
        "Responde breve, en tres puntos."
    )
    print("=" * 64)
    print("  fi_runner LIVE QUERY  (ClaudeCodeBackend, real LLM)")
    print("=" * 64)
    print(f"\n  >> {question}\n")

    t0 = time.perf_counter()
    try:
        result = await runner.run(question, request_id="france-1")
    finally:
        await runner.aclose()
    dt = (time.perf_counter() - t0) * 1000

    print(f"\n  ANSWER (in {dt:.0f} ms wall):\n")
    print("  " + result.text.replace("\n", "\n  "))
    print(f"\n  telemetry: usage={result.usage}  session={result.session_id}")


if __name__ == "__main__":
    asyncio.run(main())
