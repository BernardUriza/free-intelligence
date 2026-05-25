"""MCP tool contract for fi_core.cognitive — zero-dep metadata.

Kept separate from :mod:`fi_core.cognitive.mcp_server` (which imports the MCP
SDK) so the contract is importable WITHOUT the ``mcp`` extra. A runner can do
``from fi_core.cognitive import MCP_SERVER_NAME, MCP_TOOLS`` to build the
``mcp__<server>__<tool>`` names it allows, then spawn the actual server with
``python -m fi_core.cognitive.mcp_server`` (which does need ``mcp``).
"""

from __future__ import annotations

MCP_SERVER_NAME = "fi-core-cognitive"

MCP_TOOLS: list[dict[str, str]] = [
    {"name": "list_presets", "description": "List the bundled cognitive prompt preset ids."},
    {"name": "load_preset", "description": "Load one prompt preset (system prompt + LLM config) by id."},
    {"name": "available_transitions", "description": "List triggers + target states available from a consultation state."},
    {"name": "advance_consultation", "description": "Apply a trigger from a state and return the next state."},
    {"name": "classify_urgency", "description": "Triage symptoms into a 1-10 gravity score + urgency level with reasons."},
    {"name": "decide_extraction", "description": "Decide whether to run another extraction pass (completeness %, max 5)."},
    {"name": "score_soap", "description": "Score SOAP completeness + NOM-004 compliance and commit readiness."},
    {"name": "redux_to_event", "description": "Translate a Redux action into a domain event for the event store."},
]
