"""Workspace surface — the connectable window into what the agents build.

Authenticated, read-only views of the persistent workspace (Bernard logging in
and SEEING the files the personas accumulate over time), plus the one WRITE the
window allows: appending a house rule to the CLAUDE.md the runner reads as
project context — adding rules to his agents, live.

Path-traversal safety is the load-bearing invariant here: `path` arrives from the
wire, so the resolved target MUST stay under WORKSPACE_ROOT.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, Query

from persona_runner.core import config
from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import RuleRequest

log = structlog.get_logger()

router = APIRouter(prefix="/v1/workspace")

HOUSE_RULES_HEADER = "\n\n## House Rules (added live via /v1/workspace/rule)\n"


@router.get("")
async def workspace_list(authorization: str | None = Header(default=None)) -> dict:
    """Read-only listing of the agents' persistent workspace (relative path +
    size + mtime per file). Capped at WORKSPACE_MAX_ENTRIES; skips VCS/cache
    noise."""
    check_auth(authorization)
    root = config.WORKSPACE_ROOT
    entries: list[dict] = []
    truncated = False
    if root.exists():
        for p in sorted(root.rglob("*")):
            if p.is_dir():
                continue
            rel = p.relative_to(root)
            if any(part in config.WORKSPACE_SKIP_DIRS for part in rel.parts):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            # `as_posix()` y no `str()`: este `path` viaja en un JSON y el cliente lo
            # manda de vuelta a `/v1/workspace/file?path=`. Con `str()` el separador
            # sale el del SO del servidor, así que la MISMA API contestaría
            # `sub/data.txt` en el contenedor y `sub\data.txt` en una máquina
            # Windows — un contrato que cambia según dónde se hospeda.
            entries.append({"path": rel.as_posix(), "bytes": st.st_size, "mtime": st.st_mtime})
            if len(entries) >= config.WORKSPACE_MAX_ENTRIES:
                truncated = True
                break
    return {"root": str(root), "count": len(entries), "truncated": truncated, "files": entries}


@router.get("/file")
async def workspace_file(
    path: str = Query(..., description="workspace-relative file path"),
    authorization: str | None = Header(default=None),
) -> dict:
    """Read ONE text file from the workspace, path-traversal safe: the resolved
    target MUST stay under WORKSPACE_ROOT (a `..` escape is rejected). Read-only,
    size-capped, binary-tolerant (decoded with replacement)."""
    check_auth(authorization)
    root = config.WORKSPACE_ROOT.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(400, "path escapes workspace")
    if not target.is_file():
        raise HTTPException(404, "not a file")
    try:
        raw = target.read_bytes()
    except OSError as e:
        raise HTTPException(500, f"read failed: {type(e).__name__}") from e
    clipped = raw[: config.WORKSPACE_MAX_FILE_BYTES]
    return {
        "path": path,
        "bytes": len(clipped),
        "truncated": len(raw) > config.WORKSPACE_MAX_FILE_BYTES,
        "content": clipped.decode("utf-8", errors="replace"),
    }


@router.post("/rule")
async def workspace_add_rule(req: RuleRequest, authorization: str | None = Header(default=None)) -> dict:
    """Append a house rule to the workspace CLAUDE.md the runner reads as project
    context. Append-only (never overwrites existing content), under a clearly
    marked section; takes effect on the next fresh session (CLAUDE.md is re-read
    when a session opens)."""
    check_auth(authorization)
    rule = (req.rule or "").strip()
    if not rule:
        raise HTTPException(400, "empty rule")
    if len(rule) > 2000:
        raise HTTPException(400, "rule too long")
    claude_md = config.WORKSPACE_ROOT / "CLAUDE.md"
    existing = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    if HOUSE_RULES_HEADER not in existing:
        existing = existing.rstrip() + HOUSE_RULES_HEADER
    updated = existing.rstrip() + f"\n- {rule}\n"
    try:
        claude_md.write_text(updated, encoding="utf-8")
    except OSError as e:
        raise HTTPException(500, f"write failed: {type(e).__name__}") from e
    log.info("workspace_rule_added", rule_chars=len(rule))
    return {"ok": True, "rule": rule, "claude_md_bytes": len(updated)}
