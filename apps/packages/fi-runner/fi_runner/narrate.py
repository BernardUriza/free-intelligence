"""LLM narration of a turn-flow diagram — the model annotates its OWN turn.

:mod:`fi_runner.flow` renders what the runner sees from the OUTSIDE (telemetry
events). This module adds the INSIDE view: hand the mechanical diagram plus the
turn's request/response back to the runner's own backend and ask it to refine
the Mermaid into a dev-facing narrative — what its cognitive process actually
reasoned about in that flow, justified with notes, new edges/blocks and colors.

It's a SECOND backend call, so it's opt-in and (in the Runner) runs in the
background. The refinement is validated like a pipeline mutation: it must still
be a Mermaid flowchart and must keep the ``request_id`` anchor so the trace stays
linked to the turn. A refinement that breaks those invariants is rejected
(:class:`FlowNarrationError`) and the caller keeps the mechanical diagram.
"""

from __future__ import annotations

from .backend import AgentBackend, ToolPolicy

_SYSTEM = """\
You are annotating one of your OWN just-completed turns for the developers who \
operate you. You receive (1) a mechanical Mermaid flowchart of the turn, \
reconstructed from runtime telemetry — it shows the path the turn took: \
capability/MCP wiring, each guard and its level, retries, post-processors, \
latency/cost — and (2) the user's request and your response for that turn.

Rewrite the Mermaid flowchart so it explains to a developer what your cognitive \
process actually did in this turn and WHY. You may add nodes, edges, subgraphs \
and notes, and use classDef colors, to reveal reasoning the mechanical view \
cannot see (what you weighed, what you prioritized, what you deliberately did \
not do).

Hard rules:
- Keep the start node line carrying `request_id=<id>` VERBATIM so the trace stays \
linked to the turn.
- The telemetry is ground truth for the PATH: add meaning, never invent steps \
that did not happen.
- Output ONLY the Mermaid flowchart (it MUST start with `flowchart`). No prose, \
no explanations, no Markdown code fences."""


class FlowNarrationError(RuntimeError):
    """The model's refinement was not a usable diagram (not a flowchart, or it
    dropped the ``request_id`` anchor). The caller keeps the mechanical diagram."""


def _extract_mermaid(text: str) -> str:
    """Pull the Mermaid body out of a model reply: strip ``` fences and any prose
    before the first ``flowchart``/``graph`` line."""
    body = text.strip()
    if body.startswith("```"):
        # drop the opening fence (``` or ```mermaid) and the trailing fence
        lines = body.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        body = "\n".join(lines).strip()
    lowered = body.splitlines()
    for i, line in enumerate(lowered):
        if line.lstrip().startswith(("flowchart", "graph")):
            return "\n".join(lowered[i:]).strip()
    return body


async def narrate_flow(
    backend: AgentBackend,
    mechanical_mmd: str,
    *,
    user_message: str,
    response_text: str,
    model: str | None = None,
    instructions: str | None = None,
    request_id: str | None = None,
) -> str:
    """Ask ``backend`` to refine ``mechanical_mmd`` into a dev-facing narrative.

    Returns enriched Mermaid. Raises :class:`FlowNarrationError` if the reply
    isn't a flowchart or (when ``request_id`` is given) drops its anchor — the
    runner catches this and keeps the already-delivered mechanical diagram.
    ``model`` overrides the turn's model (e.g. a cheaper tier); ``instructions``
    appends extra guidance to the narration prompt.
    """
    payload = (
        f"{mechanical_mmd}\n\n"
        f"---\nUSER REQUEST:\n{user_message}\n\n"
        f"---\nYOUR RESPONSE:\n{response_text}\n\n"
        "---\nRewrite the flowchart now."
    )
    system = f"{_SYSTEM}\n\n{instructions}" if instructions else _SYSTEM
    result = await backend.run_turn(
        system_prompt=system,
        user_message=payload,
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        model=model,
        session_id=None,
    )
    refined = _extract_mermaid(result.text or "")
    if not refined.startswith(("flowchart", "graph")):
        raise FlowNarrationError("narration did not return a Mermaid flowchart")
    if request_id and f"request_id={request_id}" not in refined:
        raise FlowNarrationError("narration dropped the request_id anchor")
    return refined


__all__ = ["FlowNarrationError", "narrate_flow"]
