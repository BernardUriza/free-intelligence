#!/usr/bin/env python3
"""Turn flow → Mermaid — reconstruct a turn's path from its telemetry events.

The Runner emits events (turn_completed, guard_critical, mutation_applied,
backend_error, ...). This turns that event stream into a Mermaid flowchart of
the path the turn ACTUALLY took: how many MCP servers were wired, each guard and
its level (CRITICAL highlighted), retries, post-processor stages (applied or
rejected) and the final latency/tokens/cost. Same function works for any turn's
events — the French-history turn, a clinical one, a failed one.

    python3 examples/flow_mermaid.py            # write examples/turn_flow.mmd
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # noqa: E402

from dataclasses import dataclass  # noqa: E402

from fi_runner import MutationStage, Runner, TurnResult, antidrift_guard, triage_guard  # noqa: E402

_OUT = Path(__file__).parent / "turn_flow.mmd"

Event = tuple[str, dict]


def events_to_mermaid(events: list[Event], *, title: str | None = None) -> str:
    """Render a Mermaid flowchart of the path a turn took, from its events."""
    completed = next((f for e, f in events if e == "turn_completed"), {})
    mutations = [f for e, f in events if e == "mutation_applied"]
    violations = [f for e, f in events if e == "pipeline_violation"]
    criticals = {f.get("guard") for e, f in events if e == "guard_critical"}
    guard_errors = {f.get("guard") for e, f in events if e == "guard_error"}
    backend_errors = [f for e, f in events if e == "backend_error"]

    lines: list[str] = ["flowchart TD"]
    if title:
        lines.append(f"    %% {title}")

    rid = completed.get("request_id", "?")
    mcp = completed.get("mcp_count", 0)
    model = completed.get("model")
    attempts = completed.get("attempts", 1)

    lines += [
        f'    start(["run · request_id={rid}"])',
        '    validate["validate input"]',
        f'    resolve["resolve capabilities<br/>{mcp} MCP server(s)"]',
        f'    backend["backend.run_turn<br/>model={model} · attempts={attempts}"]',
        "    start --> validate --> resolve --> backend",
    ]

    crit_nodes: list[str] = []
    err_nodes: list[str] = []
    prev = "backend"

    if backend_errors:
        be = backend_errors[0]
        lines.append(f'    berr["backend_error<br/>{be.get("backend")}"]')
        lines.append("    backend -.raises.-> berr")
        err_nodes.append("berr")

    for i, (name, level) in enumerate(completed.get("guard_levels", {}).items()):
        nid = f"g{i}"
        lines.append(f'    {nid}["guard: {name} → {level}"]')
        lines.append(f"    {prev} --> {nid}")
        if name in criticals:
            crit_nodes.append(nid)
        if level == "error" or name in guard_errors:
            err_nodes.append(nid)
        prev = nid

    if attempts > 1:
        lines.append(f'    {prev} -.retry x{attempts - 1}.-> backend')

    for i, m in enumerate(mutations):
        nid = f"pp{i}"
        lines.append(f'    {nid}["post: {m.get("stage")}<br/>{m.get("before_len")}→{m.get("after_len")} chars"]')
        lines.append(f"    {prev} --> {nid}")
        prev = nid
    for i, v in enumerate(violations):
        nid = f"pv{i}"
        lines.append(f'    {nid}["post REJECTED: {v.get("stage")}<br/>{v.get("failed_invariants")}"]')
        lines.append(f"    {prev} -.rejected.-> {nid}")

    lat = completed.get("latency_ms")
    tokens = completed.get("tokens") or {}
    out_tok = tokens.get("output_tokens") if isinstance(tokens, dict) else None
    cost = tokens.get("total_cost_usd") if isinstance(tokens, dict) else None
    label = f"turn_completed<br/>{lat} ms"
    if out_tok is not None:
        label += f" · {out_tok} out tok"
    if cost is not None:
        label += f" · ${cost:.4f}"
    lines.append(f'    done(["{label}"])')
    lines.append(f"    {prev} --> done")

    lines.append("    classDef crit fill:#fdd,stroke:#c00,stroke-width:2px;")
    lines.append("    classDef err fill:#fee,stroke:#e60,stroke-dasharray:4 2;")
    if crit_nodes:
        lines.append(f"    class {','.join(crit_nodes)} crit;")
    if err_nodes:
        lines.append(f"    class {','.join(err_nodes)} err;")
    return "\n".join(lines)


@dataclass
class _FakeBackend:
    text: str

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text, usage={"output_tokens": 142, "total_cost_usd": 0.0119})


async def main() -> None:
    events: list[Event] = []
    runner = Runner(
        backend=_FakeBackend("  Con esos factores hay riesgo agudo; deriva a urgencias y activa contención.  "),
        persona="Asistente clínico de apoyo en salud mental. Directo y prudente.",
        capabilities=["cognitive", "persona"],  # -> 2 MCP servers
        guards=[triage_guard("psychiatry"), antidrift_guard(break_patterns=[])],
        post_processors=[MutationStage(name="strip", apply=lambda t, c: t.strip(), max_shrink_pct=None)],
        on_event=lambda e, f: events.append((e, f)),
    )
    # User message carries the crisis marker → triage escalates to CRITICAL.
    await runner.run("el paciente refiere plan suicida con medios letales", request_id="demo-mermaid")

    mermaid = events_to_mermaid(events, title="fi_runner turn — psychiatry, triage CRITICAL")
    _OUT.write_text(mermaid + "\n")
    print(mermaid)
    print(f"\nwritten -> {_OUT}")


if __name__ == "__main__":
    asyncio.run(main())
