"""List and fetch a casita's artifacts over HTTP — backlog #22b.

The `scp` used to rescue the books off the droplet is the tell of THIS missing
endpoint ([[ssh-is-a-missing-endpoint]]): a need met over SSH becomes a new
endpoint, not a habit. These are FILES on the droplet's disk, not database rows,
so this is the daemon's OWN surface, not a waiter read — [[write-only-daemon]] is
untouched (it governs the database, and the front cannot reach disk files anyway).
Raw bytes go back, never HTML: fetching an artifact is a download, not a view.

Path safety reuses the agent cage's `escapes` (Art. 6, one confinement rule):
`.resolve()` collapses `..` and follows symlinks, so nothing escapes the casita.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from .engine.cage import escapes
from .engine.core import WORKSPACES
from .names import InvalidName, clean

router = APIRouter()


def _root(project: str) -> Path:
    return (WORKSPACES / project).resolve()


def _safe_project(project: str) -> str:
    try:
        return clean("project", project)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def listing(project: str) -> list[str]:
    """Every file in the casita, as casita-relative paths (deepest sorted)."""
    root = _root(project)
    if not root.is_dir():
        return []
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def resolve(project: str, subpath: str) -> Path:
    """A single artifact's real path, or raise if it escapes / is missing."""
    root = _root(project)
    if escapes(root, subpath):
        raise ValueError(f"{subpath} is outside the casita")
    target = (root / subpath).resolve()
    if not target.is_file():
        raise FileNotFoundError(subpath)
    return target


@router.get("/projects/{project}/artifacts")
async def list_artifacts(project: str) -> JSONResponse:
    """The files an agent wrote in this casita — disk, not the database (#22b)."""
    project = _safe_project(project)
    return JSONResponse({"project": project, "artifacts": listing(project)})


@router.get("/projects/{project}/artifacts/{subpath:path}")
async def get_artifact(project: str, subpath: str) -> Any:
    """One artifact's raw bytes — the download that replaces `scp` (#22b)."""
    project = _safe_project(project)
    try:
        target = resolve(project, subpath)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(target, media_type="application/octet-stream", filename=target.name)
