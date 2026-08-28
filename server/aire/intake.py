"""The customs desk — what the door accepts from the wire, and what it refuses.

Split from `messages.py` (which owns the endpoint and the event stream) because
validating a request body is its own concept: every function here turns an
untrusted field into a typed value or an HTTPException, and none of them knows a
thing about SSE. The daemon is internet-open and runs as root, so this is where
"the wire may NAME a capability, never DEFINE one" is actually enforced.
"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException

from .engine import DEFAULT_MODE, MODES
from .engine.contract import Guard, RemoteTool
from .engine.guards import UnknownGuard, clean_guards, resolve
from .engine.tools import UnknownTool, clean_tools
from .engine.vision import BadImage, clean_images
from .names import InvalidName, clean

MODEL_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def safe_names(project: str, session: str) -> tuple[str, str]:
    try:
        return clean("project", project), clean("session", session)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def safe_mode(mode: str | None) -> str:
    return mode if mode in MODES else DEFAULT_MODE


def safe_tools(raw: Any, _mode: str) -> tuple[str, ...]:
    """Validate the `tools` field against the vetted registry (#29). The mode
    dial governs the BUILTIN surface only: registry tools are in-process and
    vetted, so a complete-mode turn may carry them (#36 — og118 edits its
    living persona without ever gaining Write or WebSearch)."""
    try:
        names = clean_tools(raw)
    except UnknownTool as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return tuple(names)


def safe_model(raw: Any) -> str | None:
    """The `model` field (#29 gap 3) rides verbatim to the CLI as `--model`; the
    edge guards only the argv's shape — the API curates the catalog. Absent →
    the engine decides. Binds when the session's pooled client is (re)born."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str) and MODEL_SHAPE.match(raw):
        return raw
    raise HTTPException(status_code=422, detail="invalid model")


def safe_images(raw: Any) -> tuple[dict[str, str], ...]:
    """Attachments for THIS turn (#29 gap 4), validated in `engine/vision.py`."""
    try:
        return clean_images(raw)
    except BadImage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def safe_guard_names(raw: Any) -> list[str]:
    """The `guards` field as validated NAMES — the cheap, deterministic half.

    Separate from building on purpose: a request whose SHAPE is wrong (a spec
    instead of a name, guards on a detached turn) must be refused before anything
    environmental is consulted. Otherwise a caller on a box without the backing
    gets told the backing is missing when the real problem is their request, and
    the same call would answer differently on another box."""
    try:
        return clean_guards(raw)
    except UnknownGuard as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


REMOTE_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_REMOTE_TOOLS_MAX = 4
_REMOTE_HEADERS_MAX = 8


def _allowed_remote_origins() -> frozenset[str]:
    """The origins a remote_tools url may point at — defined by the OPERATOR in
    ``AIRE_REMOTE_TOOL_ORIGINS`` (comma-separated ``https://host[:port]``), never
    by the wire. Read per-request so provisioning can add one without a restart."""
    raw = os.environ.get("AIRE_REMOTE_TOOL_ORIGINS", "")
    return frozenset(o.strip().rstrip("/").lower() for o in raw.split(",") if o.strip())


def safe_remote_tools(raw: Any) -> tuple[RemoteTool, ...]:
    """Validate `remote_tools` (#48): HTTP MCP servers the caller hosts.

    The registry doctrine holds — no command ever crosses the wire. What IS
    accepted is ``{name, url, headers?}`` where the url's origin sits in the
    operator's allowlist: the wire names a capability, the environment defines
    the trust. Everything else is a 422 that never echoes a header value."""
    if raw is None or raw == []:
        return ()
    if not isinstance(raw, list) or len(raw) > _REMOTE_TOOLS_MAX:
        raise HTTPException(status_code=422,
                            detail=f"remote_tools must be a list of at most {_REMOTE_TOOLS_MAX} specs")
    allowed = _allowed_remote_origins()
    from .engine.tools import REGISTRY
    out: list[RemoteTool] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail="each remote tool must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not REMOTE_TOOL_NAME.match(name):
            raise HTTPException(status_code=422,
                                detail="remote tool name must match ^[a-z][a-z0-9_]{0,31}$")
        if name in REGISTRY or name in seen:
            raise HTTPException(status_code=422,
                                detail=f"remote tool name {name!r} collides with the registry or repeats")
        url = item.get("url")
        if not isinstance(url, str) or len(url) > 512:
            raise HTTPException(status_code=422, detail="remote tool url must be a string (<=512 chars)")
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
            raise HTTPException(status_code=422, detail="remote tool url must be plain https")
        origin = f"https://{parts.netloc}".lower()
        if origin not in allowed:
            raise HTTPException(status_code=422,
                                detail=f"origin {origin} is not in AIRE_REMOTE_TOOL_ORIGINS")
        headers = item.get("headers") or {}
        if (not isinstance(headers, dict) or len(headers) > _REMOTE_HEADERS_MAX
                or not all(isinstance(k, str) and isinstance(v, str)
                           and len(k) <= 64 and len(v) <= 512
                           and "\n" not in k and "\r" not in k
                           and "\n" not in v and "\r" not in v for k, v in headers.items())):
            raise HTTPException(status_code=422,
                                detail=f"remote tool headers must be a small flat str map "
                                       f"(<= {_REMOTE_HEADERS_MAX} entries, no newlines)")
        seen.add(name)
        out.append(RemoteTool(name=name, url=url, headers=tuple(sorted(headers.items()))))
    return tuple(out)


def build_guards(names: list[str]) -> list[Guard]:
    """The vetted guards, built HERE at the edge before a dollar is spent. A guard
    imports its backing lazily, so a missing one would otherwise surface mid-turn
    as findings that never arrive — a request accepted and quietly unserved."""
    try:
        return resolve(names)
    except Exception as exc:  # noqa: BLE001 — the backing is absent; not the caller's fault
        raise HTTPException(status_code=503,
                            detail=f"guard backing unavailable: {type(exc).__name__}") from exc
