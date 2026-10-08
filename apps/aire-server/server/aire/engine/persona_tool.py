"""The `persona` in-process MCP server — the agent rewrites its own living identity.

Second tenant of the tool registry (backlog #36; Bernard's greenlight 2026-08-21:
casita per chat, protected base). The casita's ``CLAUDE.md`` has two halves split
by ``MARKER``: above it the PROTECTED BASE, owned by the ``init`` endpoint and
untouchable through this tool — an agent that can erase its own constraints
erases the cage's manners; below it the LIVING part this tool reads and rewrites.
The next turn's spawn re-reads the file (``options._casita_prompt``), so an
update takes effect from the very next message.

Self-confined by construction: the only path ever touched is ``<cwd>/CLAUDE.md``,
fixed at build time — no path crosses the wire. The write is tmp+rename, so a
crash can never leave a half-written identity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..agent_sdk import mcp_server as create_sdk_mcp_server
from ..agent_sdk import tool

MARKER = "<!-- AIRE:LIVING — everything below is the living persona; the base above is protected -->"
MAX_LIVING = 8_000


def split(text: str) -> tuple[str, str]:
    """(base, living) — the marker belongs to neither half."""
    if MARKER not in text:
        return text.rstrip(), ""
    base, _, living = text.partition(MARKER)
    return base.rstrip(), living.strip()


def merge(base: str, living: str) -> str:
    """The file both halves share. No living part → no marker: a casita that
    never grew one stays byte-identical to what `init` wrote."""
    if not living.strip():
        return (base.rstrip() + "\n") if base.strip() else ""
    parts = ([base.rstrip()] if base.strip() else []) + [MARKER, living.strip()]
    return "\n\n".join(parts) + "\n"


def rebase(existing: str, new_base: str) -> str:
    """A re-init keeps the living part and refreshes only the base — the other
    half of the protection: `init` owns the base, the tool owns the living."""
    return merge(new_base, split(existing)[1])


def _write(md: Path, text: str) -> None:
    tmp = md.with_name(md.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, md)


def _payload(text: str, failed: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if failed:
        out["is_error"] = True
    return out


def _read_file(md: Path) -> dict[str, Any]:
    try:
        return _payload(md.read_text(encoding="utf-8"))
    except OSError:
        return _payload("This casita has no persona file yet.")


def _apply_update(md: Path, living: str) -> dict[str, Any]:
    if len(living) > MAX_LIVING:
        return _payload(f"living persona too long ({len(living)} > {MAX_LIVING} chars)", failed=True)
    try:
        base = split(md.read_text(encoding="utf-8"))[0]
    except OSError:
        base = ""
    try:
        _write(md, merge(base, living))
    except OSError as exc:
        return _payload(f"update failed: {type(exc).__name__}", failed=True)
    verb = "updated" if living else "cleared"
    return _payload(f"Living persona {verb} ({len(living)} chars); the base is untouched.")


def build_persona_server(_project_key: str, cwd: str) -> Any:
    """The session-scoped `persona` server: read the whole identity, rewrite
    only the living half."""
    md = Path(cwd) / "CLAUDE.md"

    @tool(
        "read",
        "Read your persona file: the protected base you stand on and, below the "
        "marker, your living persona for this conversation.",
        {},
    )
    async def read(_args: dict[str, Any]) -> dict[str, Any]:
        return _read_file(md)

    @tool(
        "update",
        "Replace your LIVING persona — the part below the marker — with new text, "
        "effective from the next message. The protected base above the marker "
        "cannot be changed by this tool. Pass empty text to clear the living part.",
        {"living": str},
    )
    async def update(args: dict[str, Any]) -> dict[str, Any]:
        return _apply_update(md, str(args.get("living") or "").strip())

    return create_sdk_mcp_server(name="persona", version="1.0.0", tools=[read, update])
