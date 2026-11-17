"""`aire-projects` — a project's files, documents and chats in AIRE, as MCP tools (#55).

What a project holds in AIRE: a casita (its persona, `CLAUDE.md`), corpora of
documents (exact text, every version, full-text search) and chats (the transcript
of every session). This server lets Claude Code — or any MCP client — list, read,
write and search them over the door, and push or pull a directory tree so a repo
can keep a local working copy of research that lives in AIRE, not in git.

Register (no secret in the config; the token is read from its file per call):
    python3 -I <repo>/apps/aire-server/mcp/projects_mcp.py
CLI:
    projects_mcp.py push <dir> [--prefix p/] [--project P] [--corpus C]
    projects_mcp.py pull <dir> [--prefix p/] [--project P] [--corpus C]

Env: AIRE_PROJECT / AIRE_CORPUS name the defaults a tool falls back to, plus
`aire_gate.py`'s AIRE_GATE_URL and AIRE_TOKEN_FILE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aire_gate as gate  # noqa: E402
from aire_stdio import Tool, obj, serve  # noqa: E402

STR = {"type": "string"}
INT = {"type": "integer"}
P = {"project": {**STR, "description": "AIRE project (casita). Default: $AIRE_PROJECT."}}
C = {"corpus_id": {**STR, "description": "Corpus inside the project. Default: $AIRE_CORPUS."}}
D = {"doc_id": {**STR, "description": "Document id, usually its repo-relative path."}}


def _project(a: dict) -> str:
    name = str(a.get("project") or os.environ.get("AIRE_PROJECT", "")).strip()
    if not name:
        raise ValueError("project is required (or set AIRE_PROJECT)")
    return name


def _corpus(a: dict) -> str:
    name = str(a.get("corpus_id") or os.environ.get("AIRE_CORPUS", "")).strip()
    if not name:
        raise ValueError("corpus_id is required (or set AIRE_CORPUS)")
    return name


def _base(a: dict) -> str:
    return f"/projects/{gate.quote(_project(a))}/corpus/{gate.quote(_corpus(a))}"


def tools(http: gate.Http = gate.call) -> list[Tool]:
    """The table, bound to a transport — the real door by default, a test's otherwise."""
    return [*_project_tools(http), *_document_tools(http), *_chat_tools(http)]


def _project_tools(http: gate.Http) -> list[Tool]:
    return [
        Tool("list_projects", "List AIRE's projects (casitas) and whether each has a persona.",
             obj(), lambda a: http("GET", "/projects")),
        Tool("list_corpora", "List the corpora of a project with their document count and size.",
             obj(**P), lambda a: http("GET", f"/projects/{gate.quote(_project(a))}/corpus")),
        Tool("read_persona", "Read a project's persona: the casita's CLAUDE.md, raw.",
             obj(**P), lambda a: _artifact(http, _project(a), "CLAUDE.md")),
    ]


def _document_tools(http: gate.Http) -> list[Tool]:
    return [
        Tool("list_documents", "List a corpus's documents (doc_id, chunks, last write).",
             obj(**P, **C), lambda a: http("GET", f"{_base(a)}/documents")),
        Tool("read_document", "Read one document's exact text, the newest version or `version`.",
             obj(["doc_id"], **P, **C, **D, version=INT),
             lambda a: http("GET", f"{_base(a)}/text/{gate.quote(a['doc_id'])}",
                            query={"version": a["version"]} if a.get("version") else None)),
        Tool("write_document", "Write a document (a new version; an unchanged text appends nothing).",
             obj(["doc_id", "text"], **P, **C, **D, text=STR),
             lambda a: http("POST", f"{_base(a)}/documents", {"doc_id": a["doc_id"], "text": a["text"]})),
        Tool("search_documents", "Full-text search (Spanish stemming, accents folded) over a corpus; best passages first.",
             obj(["query"], **P, **C, query=STR, top_k=INT),
             lambda a: http("GET", f"{_base(a)}/documents/search",
                            query={"q": a["query"], "top_k": int(a.get("top_k") or 5)})),
        Tool("document_history", "Every version of one document, newest first, deletions included.",
             obj(["doc_id"], **P, **C, **D), lambda a: http("GET", f"{_base(a)}/history/{gate.quote(a['doc_id'])}")),
        Tool("delete_document", "Delete one document. Its history stays readable by version.",
             obj(["doc_id"], **P, **C, **D),
             lambda a: http("DELETE", f"{_base(a)}/documents/{gate.quote(a['doc_id'])}")),
    ]


def _chat_tools(http: gate.Http) -> list[Tool]:
    return [
        Tool("list_chats", "List a project's chats (sessions), newest activity first.",
             obj(**P), lambda a: http("GET", f"/projects/{gate.quote(_project(a))}/sessions")),
        Tool("read_chat", "Read one chat as turns (role, text), oldest first; `limit` keeps the last N.",
             obj(["session"], **P, session=STR, limit=INT),
             lambda a: http("GET", f"/projects/{gate.quote(_project(a))}/sessions/{gate.quote(a['session'])}/transcript",
                            query={"limit": int(a.get("limit") or 400)})),
    ]


def _artifact(http: gate.Http, project: str, path: str) -> object:
    return http("GET", f"/projects/{gate.quote(project)}/artifacts/{gate.quote(path)}", raw=True)


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("push", "pull"):
        from sync import run
        return run(argv)
    serve("aire-projects", tools())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
