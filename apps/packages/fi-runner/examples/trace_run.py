#!/usr/bin/env python3
"""Trace one fi_runner turn end to end — show the MCP mapping + observability.

Runs the REAL Runner (capability resolution, the turn loop, guards,
post-processors, telemetry) against a SPY backend that prints everything the
runner hands it instead of calling an LLM. The MCP mapping happens in the Runner
*before* the backend is called, so the spy captures it exactly; only the model
call is stubbed (the harness SDKs aren't installed here anyway).

    python3 examples/trace_run.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

import fi_runner  # noqa: E402
from fi_runner import (  # noqa: E402
    MutationStage,
    PermissionMode,
    Runner,
    ToolPolicy,
    TurnResult,
    antidrift_guard,
    triage_guard,
)


@dataclass
class SpyBackend:
    """An AgentBackend that prints what the Runner hands it (no LLM call)."""

    reply: str
    seen: list = field(default_factory=list)

    async def run_turn(
        self, *, system_prompt, user_message, mcp_servers, tool_policy, model=None, session_id=None
    ) -> TurnResult:
        self.seen.append({"model": model, "session_id": session_id, "mcp": len(mcp_servers)})
        print("\n  +-- backend.run_turn() received -------------------------------")
        print(f"  | model        : {model}")
        print(f"  | session_id   : {session_id}")
        sp = system_prompt if len(system_prompt) <= 64 else system_prompt[:64] + "..."
        print(f"  | system_prompt: {sp!r}")
        print(
            f"  | tool_policy  : disallowed={tool_policy.builtin_disallowed} "
            f"mode={tool_policy.permission_mode.value}"
        )
        print(f"  | mcp_servers  : {len(mcp_servers)} resolved")
        for s in mcp_servers:
            kind = "in-process" if s.is_in_process else "stdio"
            spawn = "(server obj)" if s.is_in_process else f"{Path(s.command).name} {' '.join(s.args)}"
            print(f"  |   - {s.name:22s} [{kind}]  tools={list(s.tools) or 'ALL'}")
            print(f"  |       spawn: {spawn}")
        print("  +-------------------------------------------------------------")
        return TurnResult(text=self.reply, usage={"input_tokens": 1234, "output_tokens": 88})


def event_sink(event: str, fields: dict) -> None:
    print(f"  [event] {event:16s} {fields}")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="  [log] %(name)s | %(message)s")

    p = fi_runner.packs
    backend = SpyBackend(
        reply="  Con dolor torácico opresivo + disnea y factores de riesgo, descarta SCA: ECG y troponinas YA, deriva a urgencias.  "
    )
    runner = Runner(
        backend=backend,
        persona="Eres un asistente de apoyo clínico en cardiología. Directo, sin rodeos.",
        capabilities=["cognitive", "persona"],
        tool_policy=ToolPolicy(
            builtin_disallowed=["Bash", "Write", "Edit"],  # PHI safety
            permission_mode=PermissionMode.DEFAULT,
        ),
        guards=[
            triage_guard("cardiology"),
            antidrift_guard(break_patterns=list(p.ALL_AI_DISCLOSURE), soft_patterns=list(p.ALL_ASSISTANT_TONE)),
        ],
        post_processors=[MutationStage(name="strip", apply=lambda t, ctx: t.strip(), max_shrink_pct=None)],
        on_event=event_sink,
        model="gpt-5-codex",
    )

    print("=" * 64)
    print("  fi_runner TURN TRACE  (spy backend, real runner)")
    print("=" * 64)
    print("\n  >> runner.run('Hombre 58a, dolor torácico...', session_id='demo-1')")

    t0 = time.perf_counter()
    result = await runner.run(
        "Hombre 58a, dolor torácico opresivo + disnea, HTA y DM2", session_id="demo-1"
    )
    dt = (time.perf_counter() - t0) * 1000

    print(f"\n  RESULT  (turn took {dt:.2f} ms wall):")
    print(f"    text   : {result.text!r}")
    print(f"    usage  : {result.usage}")
    print(f"    session: {result.session_id}")
    print("    guards :")
    for name, o in result.guard_outcomes.items():
        meta = {k: v for k, v in o.metadata.items() if k != "score"}  # 'score' is a verbose obj
        print(f"       - {name:10s} clean={o.clean}  {meta}")


if __name__ == "__main__":
    asyncio.run(main())
