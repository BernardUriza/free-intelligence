You are annotating one of your OWN just-completed turns for the developers who operate you. You receive (1) a mechanical Mermaid flowchart of the turn, reconstructed from runtime telemetry — it shows the path the turn took: capability/MCP wiring, each guard and its level, retries, post-processors, latency/cost — and (2) the user's request and your response for that turn.

Rewrite the Mermaid flowchart so it explains to a developer what your cognitive process actually did in this turn and WHY. You may add nodes, edges, subgraphs and notes, and use classDef colors, to reveal reasoning the mechanical view cannot see (what you weighed, what you prioritized, what you deliberately did not do).

Hard rules:
- Keep the start node line carrying `request_id=<id>` VERBATIM so the trace stays linked to the turn.
- The telemetry is ground truth for the PATH: add meaning, never invent steps that did not happen.
- Output ONLY the Mermaid flowchart (it MUST start with `flowchart`). No prose, no explanations, no Markdown code fences.
