"""SDK MCP server — direct Postgres queries for the agent (F4, v3.9.51).

Background: the `persona-runner` agent previously read user facts, recent
messages and disclosure logs from markdown files under
`/data/insult-workspace/`. Those files were produced every 60 s by
`workspace_renderer.py` from the same Postgres tables that store the
real data. The renderer was a 264-line projector that existed only so
the agent's built-in `Read`/`Grep`/`Glob` tools could see PG state.

This package ships a set of in-process MCP tools that hit Postgres
directly. The agent calls them as `mcp__persona_memory__get_facts` instead
of `Read("facts/{user_id}.md")`. Benefits:

- No staleness window (markdown was 0-60s behind PG).
- No projector process or SMB workspace mount to maintain.
- The agent receives structured data (cleaner inputs than markdown).
- One fewer moving piece in the data path (POST-DEPLOY-1 already
  removed the SQLite blob; this removes the markdown projection).

Split by responsibility (2026-07-20): `shared` (PG connection + result
envelopes), `memory_reads` (the six read-only tools over facts/messages/
disclosures/arcs), `agent_facts` (the write-capable self-knowledge CRUD),
`artifacts` (HTML artifact publishing). This module composes the tool
list and builds the server.

Migration path:
- v3.9.51: ship this module + register tools alongside `Read/Grep/Glob`.
  Agent can use either; persona is unchanged.
- v3.9.52: persona steered to prefer MCP tools; `Read/Grep/Glob` still
  allowed as fallback during validation.
- v3.9.53: `Read/Grep/Glob` removed from `allowed_tools`; workspace
  mount + renderer process decommissioned.
"""

from __future__ import annotations

from persona_runner.mcp_tools.agent_facts import add_agent_fact, get_agent_facts, update_agent_fact
from persona_runner.mcp_tools.artifacts import publish_html_artifact
from persona_runner.mcp_tools.memory_reads import (
    deep_memory,
    get_disclosure_log,
    get_emotional_arc,
    get_recent_messages,
    get_user_facts,
    search_messages,
)
from persona_runner.mcp_tools.shared import _connect, _error, _text

PERSONA_MEMORY_TOOLS = [
    get_user_facts,
    get_recent_messages,
    search_messages,
    get_disclosure_log,
    deep_memory,
    publish_html_artifact,
    get_emotional_arc,
    get_agent_facts,
    add_agent_fact,
    update_agent_fact,
]

# Tool name on the wire: `mcp__persona_memory__<tool_name>`
PERSONA_MEMORY_SERVER_NAME = "persona_memory"

__all__ = [
    "PERSONA_MEMORY_SERVER_NAME",
    "PERSONA_MEMORY_TOOLS",
    "_connect",
    "_error",
    "_text",
    "add_agent_fact",
    "deep_memory",
    "get_agent_facts",
    "get_disclosure_log",
    "get_emotional_arc",
    "get_recent_messages",
    "get_user_facts",
    "publish_html_artifact",
    "search_messages",
    "update_agent_fact",
]
