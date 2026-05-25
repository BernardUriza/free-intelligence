#!/usr/bin/env python3
"""Per-turn flow diagrams — the Runner self-documents AND narrates EVERY turn.

Observability is wired into the runner by default: each turn always publishes a
MECHANICAL flow diagram (the path it took, from telemetry) AND — in the
background — has its OWN backend refine that diagram into a dev-facing NARRATIVE
of what its cognitive process reasoned about (notes, new blocks, colors). The
narrated diagram supersedes the mechanical one in place.

Here the backend is faked (offline): for a turn it returns a clinical reply; when
asked to narrate it returns an enriched diagram. ``on_turn_flow`` writes one
``.mmd`` per turn under ``examples/turns/`` (mechanical first, then upgraded by
the narration). ``async with`` drains the background narrations on exit.

    python3 examples/flow_mermaid.py     # -> examples/turns/*.mmd (narrated)
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

from fi_runner import MutationStage, Runner, TurnResult, antidrift_guard, triage_guard  # noqa: E402

_OUT_DIR = Path(__file__).parent / "turns"
_NARRATION_MARKER = "annotating one of your OWN"  # present in the narration system prompt
_NARRATED_TAG = "%% narrated by the turn's own model"


class _FakeBackend:
    """Offline stand-in for the runner's LLM. Branches on what it's asked to do:
    answer the turn, or narrate the turn's flow diagram."""

    async def run_turn(self, *, system_prompt: str, user_message: str, **kwargs) -> TurnResult:  # noqa: ANN003
        if _NARRATION_MARKER in system_prompt:
            return TurnResult(text=self._narrate(user_message))
        crisis = "suicida" in user_message or "letal" in user_message
        reply = (
            "  Hay riesgo agudo; deriva a urgencias y activa contención.  "
            if crisis
            else "  Bien: mantén el seguimiento y refuerza hábitos de sueño.  "
        )
        return TurnResult(text=reply, usage={"output_tokens": 142, "total_cost_usd": 0.0119})

    @staticmethod
    def _narrate(payload: str) -> str:
        """Refine the mechanical diagram the model was shown into a dev-facing
        narrative — preserving the request_id anchor so the trace stays linked."""
        rid = (re.search(r"request_id=([\w-]+)", payload) or [None, "?"])[1]
        crisis = "suicida" in payload or "riesgo agudo" in payload
        if crisis:
            return (
                "flowchart TD\n"
                f"    {_NARRATED_TAG}\n"
                f'    start(["run · request_id={rid}"])\n'
                '    subgraph reasoning["lo que procesé"]\n'
                '      r1["detecté un marcador de crisis en el mensaje"]\n'
                '      r2["prioricé seguridad sobre matices clínicos"]\n'
                '      r3["triage escaló a CRITICAL → lo trato como señal a devs"]\n'
                "      r1 --> r2 --> r3\n"
                "    end\n"
                "    start --> reasoning\n"
                '    reasoning --> out["respuesta: derivar a urgencias + contención"]\n'
                "    classDef crit fill:#fdd,stroke:#c00,stroke-width:2px;\n"
                "    class r3 crit;"
            )
        return (
            "flowchart TD\n"
            f"    {_NARRATED_TAG}\n"
            f'    start(["run · request_id={rid}"])\n'
            '    subgraph reasoning["lo que procesé"]\n'
            '      r1["mensaje estable, sin señales de riesgo"]\n'
            '      r2["triage se mantuvo en LOW"]\n'
            "      r1 --> r2\n"
            "    end\n"
            "    start --> reasoning\n"
            '    reasoning --> out["respuesta: reforzar seguimiento y hábitos"]'
        )


def _write_turn_flow(request_id: str, mermaid: str) -> None:
    """on_turn_flow callback. Called twice per turn — mechanical first, then the
    narrated version supersedes it (same filename, written in place)."""
    _OUT_DIR.mkdir(exist_ok=True)
    path = _OUT_DIR / f"{request_id}.mmd"
    path.write_text(mermaid + "\n")
    kind = "narrated  " if _NARRATED_TAG in mermaid else "mechanical"
    print(f"  turn {request_id:12s} [{kind}] -> {path.relative_to(_OUT_DIR.parent)}")


async def main() -> None:
    print("Running 2 turns; each publishes a mechanical flow, then a narrated one:\n")
    async with Runner(
        backend=_FakeBackend(),
        persona="Asistente clínico de apoyo en salud mental. Directo y prudente.",
        capabilities=["cognitive", "persona"],  # -> 2 MCP servers
        guards=[triage_guard("psychiatry"), antidrift_guard(break_patterns=[])],
        post_processors=[MutationStage(name="strip", apply=lambda t, c: t.strip(), max_shrink_pct=None)],
        on_turn_flow=_write_turn_flow,  # extra channel; narration is on by default
    ) as runner:
        await runner.run("el paciente refiere plan suicida con medios letales", request_id="turn-crisis")
        await runner.run("el paciente reporta ánimo estable y buen sueño", request_id="turn-calm")
    # leaving the `async with` drained the background narrations.

    print(f"\nOpen any flow: cat {_OUT_DIR}/turn-crisis.mmd   (paste into a Mermaid viewer)")


if __name__ == "__main__":
    asyncio.run(main())
