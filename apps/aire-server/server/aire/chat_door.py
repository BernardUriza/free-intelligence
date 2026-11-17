"""The chat door — which projects exist, which chats a project holds, and what was
said in one (#55). JSON for an agent, never a view: the front still renders
transcripts for human eyes ([[write-only-daemon]]); this hands a project's own
chats to the agent working on it, the way `recall` hands them to the model.

Constant tokens only (`intake.owners_only`): an invited key owns no project here,
and a transcript is the most private thing AIRE keeps.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from . import transcripts
from .engine.core import WORKSPACES
from .intake import owners_only, safe_names

router = APIRouter()


def casitas() -> list[dict]:
    """Every casita on disk, and whether it carries a persona (`CLAUDE.md`)."""
    if not WORKSPACES.is_dir():
        return []
    return [{"project": d.name, "persona": (d / "CLAUDE.md").is_file()}
            for d in sorted(WORKSPACES.iterdir()) if d.is_dir() and not d.name.startswith(".")]


@router.get("/projects")
async def list_projects(request: Request) -> JSONResponse:
    owners_only(request)
    return JSONResponse({"projects": casitas()})


@router.get("/projects/{project}/sessions")
async def list_sessions(project: str, request: Request) -> JSONResponse:
    """The project's chats, newest activity first. A session is named by the UUID
    AIRE keeps it under: a readable name is hashed one-way (`keys.py`), and the
    UUID resumes the same session on the message door."""
    owners_only(request)
    project, _ = safe_names(project, "sessions")
    return JSONResponse({"project": project, "sessions": await transcripts.sessions(project)})


@router.get("/projects/{project}/sessions/{session}/transcript")
async def read_transcript(project: str, session: str, request: Request,
                          limit: int = transcripts.MAX_TURNS) -> JSONResponse:
    """What was said in one chat, oldest first — the last `limit` turns."""
    owners_only(request)
    project, session = safe_names(project, session)
    return JSONResponse({"project": project, "session": session,
                         "turns": await transcripts.turns(project, session, limit)})
