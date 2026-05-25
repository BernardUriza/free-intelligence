"""Turn flow → Mermaid — reconstruct a turn's path from its telemetry events.

The Runner emits events (``turn_completed``, ``guard_critical``,
``mutation_applied``, ``backend_error``, ...). :func:`events_to_mermaid` turns
that event stream into a Mermaid flowchart of the path the turn ACTUALLY took:
how many MCP servers were wired, each guard and its level (CRITICAL highlighted),
retries, post-processor stages (applied or rejected) and the final
latency/tokens/cost. The same function works for any turn's events — a clinical
turn, the French-history one, or a turn that crashed in the backend.

Pure and dep-free: it reads a ``list[(event_name, fields)]`` and returns a
string. The Runner calls it once per turn (when ``on_turn_flow`` is set) so each
turn self-documents what it did; a consumer can also call it offline over events
it captured through ``on_event``.
"""

from __future__ import annotations

from typing import Any

#: One telemetry event as captured from a sink: ``(event_name, fields)``.
Event = tuple[str, dict[str, Any]]


def events_to_mermaid(events: list[Event], *, title: str | None = None) -> str:
    """Render a Mermaid flowchart of the path a turn took, from its events.

    ``events`` is the ordered telemetry of a single turn. A turn that crashed
    (only ``backend_error``, no ``turn_completed``) still renders — the error
    node is highlighted instead of a completion node carrying latency/cost.
    """
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

    if completed:
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


__all__ = ["Event", "events_to_mermaid"]
