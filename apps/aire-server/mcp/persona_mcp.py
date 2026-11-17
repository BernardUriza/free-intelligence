"""`aire-persona` — talk to a project's persona in AIRE from Claude Code (#55).

A persona in AIRE is a casita: its `CLAUDE.md` (Codex reads it as `AGENTS.md`) is
who it is, and a session name is a conversation it remembers on any box, because
the transcript lives in Postgres. videopipe's script writer, GPT-6 Astra, is the
casita `videopipe` with `provider: codex` and `model: gpt-6-astra`. This server
sends a turn to the message door and returns what the persona answered; the same
`session` resumes the same conversation.

The persona reads its project as context mid-turn through AIRE's own tools, not
through a pasted package: `rag_store` searches the project's documents and
`memory` recalls its other chats. `corpus_id` tells it which corpus to search.

Register: python3 -I <repo>/apps/aire-server/mcp/persona_mcp.py
Env (defaults a call may override): AIRE_PROJECT, AIRE_CORPUS, AIRE_PERSONA_PROVIDER,
AIRE_PERSONA_MODEL, AIRE_PERSONA_MODE (complete), AIRE_PERSONA_TOOLS (comma list),
plus `aire_gate.py`'s AIRE_GATE_URL and AIRE_TOKEN_FILE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aire_gate as gate  # noqa: E402
from aire_stdio import Tool, obj, serve  # noqa: E402
from projects_mcp import P, STR, _artifact, _project  # noqa: E402

LIST = {"type": "array", "items": STR}


def turn_body(a: dict) -> dict:
    """The message door's body from the call and the env defaults; empty fields stay out."""
    tools = a.get("tools")
    if tools is None:
        tools = [t.strip() for t in os.environ.get("AIRE_PERSONA_TOOLS", "").split(",") if t.strip()]
    corpus = str(a.get("corpus_id") or os.environ.get("AIRE_CORPUS", "")).strip()
    message = str(a.get("message", "")).strip()
    if corpus and "rag_store" in tools:
        message = (f"[Project corpus: `{corpus}`. Search it with search_documents / list_documents and"
                   f" corpus_id=\"{corpus}\" before you state anything the case file should back.]\n\n{message}")
    body: dict[str, Any] = {"message": message, "tools": tools,
                            "mode": a.get("mode") or os.environ.get("AIRE_PERSONA_MODE", "complete"),
                            "provider": a.get("provider") or os.environ.get("AIRE_PERSONA_PROVIDER", ""),
                            "model": a.get("model") or os.environ.get("AIRE_PERSONA_MODEL", "")}
    return {k: v for k, v in body.items() if v not in ("", None, [])}


def ask(a: dict, stream: gate.Stream = gate.sse) -> dict:
    """One turn: what the persona said, which model said it, which tools it used."""
    if not str(a.get("message", "")).strip():
        raise ValueError("message is required")
    session = str(a.get("session") or "").strip()
    if not session:
        raise ValueError("session is required: the same name resumes the same conversation")
    path = f"/projects/{gate.quote(_project(a))}/sessions/{gate.quote(session)}/messages"
    said, result, errors = [], {}, []
    for event, data in stream("POST", path, turn_body(a)):
        if event == "text" and isinstance(data, dict):
            said.append(data.get("text", ""))
        elif event == "result" and isinstance(data, dict):
            result = data.get("result") or {}
        elif event == "error":
            errors.append(data)
    reply = result.get("answer") or result.get("text") or "".join(said)
    if errors or result.get("error") or not reply.strip():
        raise gate.GateError(f"the persona did not answer: {errors or result.get('error') or 'empty reply'}")
    return {"session": session, "reply": reply, "model": result.get("model"),
            "tools_used": [t.get("name") for t in result.get("tool_calls") or []]}


def tools(http: gate.Http = gate.call, stream: gate.Stream = gate.sse) -> list[Tool]:
    return [
        Tool("ask_persona", "Send a message to a project's persona and get its reply. The same `session` "
             "resumes the same conversation (it remembers it); a new name starts a fresh one. With "
             "tools [rag_store, memory] the persona reads the project's documents and chats itself.",
             obj(["message", "session"], **P, message=STR, session=STR, provider=STR, model=STR,
                 mode=STR, tools=LIST, corpus_id=STR), lambda a: ask(a, stream)),
        Tool("session_exists", "Does this session already hold a conversation AIRE can resume?",
             obj(["session"], **P, session=STR, provider=STR),
             lambda a: http("GET", f"/projects/{gate.quote(_project(a))}/sessions/{gate.quote(a['session'])}",
                            query={"provider": a["provider"]} if a.get("provider") else None)),
        Tool("read_persona", "Read the persona: the casita's CLAUDE.md, raw.",
             obj(**P), lambda a: _artifact(http, _project(a), "CLAUDE.md")),
        Tool("set_persona", "Replace the persona's BASE prompt (the casita's CLAUDE.md). A living part the "
             "persona wrote about itself below its marker survives.",
             obj(["text"], **P, text=STR),
             lambda a: http("POST", f"/projects/{gate.quote(_project(a))}/init", {"claude_md": a["text"]})),
    ]


if __name__ == "__main__":
    serve("aire-persona", tools())
