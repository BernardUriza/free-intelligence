"""The `init` endpoint — set a casita's FIXED prompt once, so consumers send only
the changing values (Bernard's optimization, 2026-07-21).

`POST /projects/{p}/init {claude_md}` creates the casita and writes its
`CLAUDE.md`. The engine reads that file directly into the session's system_prompt
(`options._casita_prompt`), so the consumer's persona lives as CONTENT in the
casita — not repeated inside every message, and editable without a redeploy
([[prompts-as-content-not-code]]). Idempotent: re-init refreshes the BASE only —
a living persona below the `persona` tool's marker (#36) survives, because init
owns the base and the tool owns the living, never each other's half.

Write path, not a waiter read — it creates a workspace file the daemon owns, like
the MKDIR verb, so [[write-only-daemon]] (which governs the database) is untouched.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .engine.core import WORKSPACES
from .engine.persona_tool import rebase
from .names import InvalidName, clean

router = APIRouter()


@router.post("/projects/{project}/init")
async def init_project(project: str, request: Request) -> JSONResponse:
    try:
        project = clean("project", project)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    body = await request.json()
    claude_md = str(body.get("claude_md", "")).strip()
    root = (WORKSPACES / project).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if claude_md:
        md = root / "CLAUDE.md"
        try:
            existing = md.read_text(encoding="utf-8")
        except OSError:
            existing = ""
        md.write_text(rebase(existing, claude_md), encoding="utf-8")
    return JSONResponse({"project": project, "prompt_bytes": len(claude_md)})
